from extensions import db
from models.shipment import Shipment
from models.order import Order
from models.order_status_history import OrderStatusHistory
from sqlalchemy import text
from datetime import datetime
import pytz


# Allowed status transitions cho Shipper (spec API 54)
SHIPPER_STATUS_TRANSITIONS = {
    'ASSIGNED':         'PICKED_UP',
    'PICKED_UP':        'SHIPPING',
    'SHIPPING':         ('DELIVERED', 'DELIVERY_FAILED'),   # 2 nhánh
}


class ShipmentService:

    # ── API 52: GET /api/v1/shipments/:orderId | Customer ────────────────────
    @staticmethod
    def track_shipment(order_id, customer_id):
        try:
            sql = text("""
                SELECT s.shipment_id, s.tracking_code, s.shipment_status,
                       s.assigned_at, s.picked_up_at,
                       s.delivered_at, s.failed_reason, s.created_at, s.updated_at
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
                WHERE s.order_id = :oid
                  AND o.customer_id = :uid
            """)
            row = db.session.execute(sql, {
                'oid': order_id,
                'uid': customer_id
            }).fetchone()

            if not row:
                # Kiểm tra xem order có tồn tại và thuộc customer không
                order = db.session.query(Order).filter(
                    Order.order_id == order_id,
                    Order.customer_id == customer_id,
                    Order.deleted_at.is_(None)
                ).first()
                if not order:
                    return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404
                # Order tồn tại nhưng chưa có shipment
                return {'success': False, 'message': 'Đơn hàng chưa được giao vận (chưa READY_TO_SHIP)'}, 404

            return {
                'success': True,
                'data': {
                    'shipment_id': row.shipment_id,
                    'order_id': order_id,
                    'tracking_code': row.tracking_code,
                    'shipment_status': row.shipment_status,
                    'assigned_at': row.assigned_at.isoformat() if row.assigned_at else None,
                    'picked_up_at': row.picked_up_at.isoformat() if row.picked_up_at else None,
                    'delivered_at': row.delivered_at.isoformat() if row.delivered_at else None,
                    'failed_reason': row.failed_reason,
                    'created_at': row.created_at.isoformat() if row.created_at else None,
                }
            }, 200

        except Exception as e:
            raise e

    # ── API 53: GET /api/v1/shipper/shipments | Shipper ──────────────────────
    @staticmethod
    def list_assigned_shipments(shipper_user_id, status=None, page=1, limit=20):
        try:
            offset = (page - 1) * limit

            # Count
            count_sql = text("""
                SELECT COUNT(*) AS total
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
                WHERE s.shipper_user_id = :uid
                  {status_filter}
            """.format(
                status_filter="AND s.shipment_status = :status" if status else ""
            ))
            params = {'uid': shipper_user_id}
            if status:
                params['status'] = status

            total_items = db.session.execute(count_sql, params).scalar() or 0

            # Data
            data_sql = text("""
                SELECT s.shipment_id, s.order_id, s.tracking_code, 
                       s.shipment_status, s.assigned_at, s.picked_up_at,
                       s.delivered_at, s.failed_reason, s.created_at,
                       o.order_code, o.recipient_name, o.shipping_province,
                       o.shipping_district, o.shipping_address_line
                FROM shipments s
                JOIN orders o ON s.order_id = o.order_id
                WHERE s.shipper_user_id = :uid
                  {status_filter}
                ORDER BY s.assigned_at DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """.format(
                status_filter="AND s.shipment_status = :status" if status else ""
            ))
            params['offset'] = offset
            params['limit'] = limit
            rows = db.session.execute(data_sql, params).fetchall()

            shipments = []
            for r in rows:
                shipments.append({
                    'shipment_id': r.shipment_id,
                    'order_id': r.order_id,
                    'order_code': r.order_code,
                    'tracking_code': r.tracking_code,
                    'shipment_status': r.shipment_status,
                    'recipient_name': r.recipient_name,
                    'shipping_province': r.shipping_province,
                    'shipping_district': r.shipping_district,
                    'shipping_address_line': r.shipping_address_line,
                    'assigned_at': r.assigned_at.isoformat() if r.assigned_at else None,
                    'picked_up_at': r.picked_up_at.isoformat() if r.picked_up_at else None,
                    'delivered_at': r.delivered_at.isoformat() if r.delivered_at else None,
                    'failed_reason': r.failed_reason,
                })

            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

            return {
                'success': True,
                'data': {
                    'shipments': shipments,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_items': total_items,
                        'total_pages': total_pages,
                    }
                }
            }, 200

        except Exception as e:
            raise e

    # ── API 54: PATCH /api/v1/shipper/shipments/:id/status | Shipper ─────────
    @staticmethod
    def update_shipment_status(shipment_id, shipper_user_id, new_status, failed_reason=None):
        try:
            shipment = db.session.query(Shipment).filter(
                Shipment.shipment_id == shipment_id
            ).first()

            if not shipment:
                return {'success': False, 'message': 'Lô hàng không tồn tại'}, 404

            # Verify shipper sở hữu shipment này
            if shipment.shipper_user_id != shipper_user_id:
                return {'success': False, 'message': 'Bạn không được giao lô hàng này'}, 403

            current_status = shipment.shipment_status
            allowed = SHIPPER_STATUS_TRANSITIONS.get(current_status)

            # Validate transition
            if allowed is None:
                return {
                    'success': False,
                    'message': f'Trạng thái {current_status} không thể cập nhật thêm'
                }, 400

            if isinstance(allowed, tuple):
                if new_status not in allowed:
                    return {
                        'success': False,
                        'message': f'Từ {current_status} chỉ được chuyển sang: {" hoặc ".join(allowed)}'
                    }, 400
            else:
                if new_status != allowed:
                    return {
                        'success': False,
                        'message': f'Từ {current_status} chỉ được chuyển sang: {allowed}'
                    }, 400

            # DELIVERY_FAILED bắt buộc có failed_reason
            if new_status == 'DELIVERY_FAILED' and not (failed_reason and failed_reason.strip()):
                return {'success': False, 'message': 'failed_reason là bắt buộc khi giao hàng thất bại'}, 400

            utc = pytz.UTC
            now = datetime.now(utc)

            # Cập nhật timestamps tương ứng
            shipment.shipment_status = new_status
            shipment.status = new_status  # giữ đồng bộ cột backward-compat
            shipment.updated_at = now

            if new_status == 'PICKED_UP':
                shipment.picked_up_at = now
                shipment.shipped_at = now   # alias backward-compat

            elif new_status == 'DELIVERED':
                shipment.delivered_at = now

            elif new_status == 'DELIVERY_FAILED':
                shipment.failed_reason = failed_reason.strip() if failed_reason else None

            # Cập nhật Orders + ghi status history
            order = db.session.query(Order).filter(
                Order.order_id == shipment.order_id
            ).first()

            if order:
                prev_order_status = order.order_status

                if new_status == 'DELIVERED':
                    order.order_status = 'COMPLETED'
                    order.completed_at = now
                    order.updated_at = now

                    db.session.add(OrderStatusHistory(
                        order_id=order.order_id,
                        prev_status=prev_order_status,
                        new_status='COMPLETED',
                        changed_by=shipper_user_id,
                        note='Giao hàng thành công',
                        created_at=now
                    ))

                elif new_status == 'DELIVERY_FAILED':
                    order.order_status = 'DELIVERY_FAILED'
                    order.updated_at = now

                    db.session.add(OrderStatusHistory(
                        order_id=order.order_id,
                        prev_status=prev_order_status,
                        new_status='DELIVERY_FAILED',
                        changed_by=shipper_user_id,
                        note=failed_reason,
                        created_at=now
                    ))

            db.session.commit()

            return {
                'success': True,
                'data': {
                    'shipment_id': shipment.shipment_id,
                    'shipment_status': shipment.shipment_status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e
