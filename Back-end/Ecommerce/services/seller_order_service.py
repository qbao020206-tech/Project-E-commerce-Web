from extensions import db
from models.order import Order
from models.order_item import OrderItem
from models.order_status_history import OrderStatusHistory
from models.store import Store
from models.user_store import UserStore
from models.user import User
from models.shipment import Shipment
from datetime import datetime
import pytz


# Allowed status transitions cho Seller
SELLER_STATUS_TRANSITIONS = {
    'PENDING': 'CONFIRMED',
    'CONFIRMED': 'PROCESSING',
    'PROCESSING': 'READY_TO_SHIP',
}


class SellerOrderService:

    @staticmethod
    def _get_seller_store_id(user_id):
        result = db.session.query(UserStore.store_id).filter(
            UserStore.user_id == user_id,
            UserStore.store_member_role == 'OWNER',
            UserStore.is_active == 1
        ).first()
        return result[0] if result else None

    # API 38: GET /api/v1/seller/orders
    @staticmethod
    def list_store_orders(user_id, status=None, page=1, limit=20):
        try:
            store_id = SellerOrderService._get_seller_store_id(user_id)
            if not store_id:
                return {'success': False, 'message': 'Bạn không phải chủ cửa hàng'}, 403

            offset = (page - 1) * limit

            query = db.session.query(Order).filter(
                Order.store_id == store_id,
                Order.deleted_at.is_(None)
            )

            if status:
                query = query.filter(Order.order_status == status)

            total_items = query.count()
            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0

            orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

            orders_list = []
            for o in orders:
                customer = db.session.query(User.full_name).filter(
                    User.user_id == o.customer_id
                ).first()

                orders_list.append({
                    'order_id': o.order_id,
                    'order_code': o.order_code,
                    'order_status': o.order_status,
                    'total_amount': float(o.total_amount),
                    'created_at': o.created_at.isoformat() if o.created_at else None,
                    'customer_name': customer[0] if customer else None,
                })

            return {
                'success': True,
                'data': {
                    'orders': orders_list,
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

    # API 39: GET /api/v1/seller/orders/:id
    @staticmethod
    def get_store_order_detail(user_id, order_id):
        try:
            store_id = SellerOrderService._get_seller_store_id(user_id)
            if not store_id:
                return {'success': False, 'message': 'Bạn không phải chủ cửa hàng'}, 403

            order = db.session.query(Order).filter(
                Order.order_id == order_id,
                Order.deleted_at.is_(None)
            ).first()

            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404

            if order.store_id != store_id:
                return {'success': False, 'message': 'Đơn hàng không thuộc cửa hàng của bạn'}, 403

            # Order items
            items = db.session.query(OrderItem).filter(
                OrderItem.order_id == order_id
            ).all()

            items_list = [{
                'order_item_id': oi.order_item_id,
                'product_id': oi.product_id,
                'quantity': oi.quantity,
                'unit_price': float(oi.unit_price),
                'product_name_snapshot': oi.product_name_snapshot,
                'product_image_url_snapshot': oi.product_image_url_snapshot,
            } for oi in items]

            # Customer info
            customer = db.session.query(User).filter(
                User.user_id == order.customer_id
            ).first()

            customer_info = {
                'full_name': customer.full_name if customer else None,
                'phone': customer.phone if customer else None,
            }

            # Shipment (LEFT JOIN)
            shipment = db.session.query(Shipment).filter(
                Shipment.order_id == order_id
            ).first()

            shipment_info = None
            if shipment:
                shipment_info = {
                    'status': shipment.status,
                    'tracking_code': shipment.tracking_code,
                    'carrier': shipment.carrier,
                    'shipped_at': shipment.shipped_at.isoformat() if shipment.shipped_at else None,
                    'delivered_at': shipment.delivered_at.isoformat() if shipment.delivered_at else None,
                }

            return {
                'success': True,
                'data': {
                    'order_id': order.order_id,
                    'order_code': order.order_code,
                    'order_status': order.order_status,
                    'recipient_name': order.recipient_name,
                    'recipient_phone': order.recipient_phone,
                    'shipping_address_line': order.shipping_address_line,
                    'shipping_ward': order.shipping_ward,
                    'shipping_district': order.shipping_district,
                    'shipping_province': order.shipping_province,
                    'payment_method': order.payment_method,
                    'customer_note': order.customer_note,
                    'subtotal': float(order.subtotal),
                    'discount_amount': float(order.discount_amount),
                    'shipping_fee': float(order.shipping_fee),
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'items': items_list,
                    'customer': customer_info,
                    'shipment': shipment_info,
                }
            }, 200

        except Exception as e:
            raise e

    # API 40: PATCH /api/v1/orders/:id/status
    @staticmethod
    def update_order_status(user_id, order_id, new_status, change_note=None):
        try:
            store_id = SellerOrderService._get_seller_store_id(user_id)
            if not store_id:
                return {'success': False, 'message': 'Bạn không phải chủ cửa hàng'}, 403

            order = db.session.query(Order).filter(
                Order.order_id == order_id,
                Order.deleted_at.is_(None)
            ).first()

            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404

            if order.store_id != store_id:
                return {'success': False, 'message': 'Đơn hàng không thuộc cửa hàng của bạn'}, 403

            # Kiểm tra transition hợp lệ
            current = order.order_status
            allowed_next = SELLER_STATUS_TRANSITIONS.get(current)

            if not allowed_next or allowed_next != new_status:
                return {
                    'success': False,
                    'message': f'Không thể chuyển từ {current} sang {new_status}. '
                               f'Chỉ được: {current} → {allowed_next}' if allowed_next
                               else f'Trạng thái {current} không thể cập nhật'
                }, 400

            utc = pytz.UTC
            now = datetime.now(utc)

            prev_status = order.order_status
            order.order_status = new_status
            order.updated_at = now

            # INSERT status history
            history = OrderStatusHistory(
                order_id=order.order_id,
                prev_status=prev_status,
                new_status=new_status,
                changed_by=user_id,
                note=change_note,
                created_at=now
            )
            db.session.add(history)

            # Nếu READY_TO_SHIP → tự động tạo shipment
            if new_status == 'READY_TO_SHIP':
                shipment = Shipment(
                    order_id=order.order_id,
                    status='PENDING_ASSIGNMENT',
                    created_at=now,
                    updated_at=now
                )
                db.session.add(shipment)

            db.session.commit()

            return {
                'success': True,
                'data': {
                    'order_id': order.order_id,
                    'order_status': order.order_status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # API 41: GET /api/v1/orders/:id/history — Seller hoặc Admin
    @staticmethod
    def get_order_status_history(user_id, roles, order_id):
        try:
            order = db.session.query(Order).filter(
                Order.order_id == order_id,
                Order.deleted_at.is_(None)
            ).first()

            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404

            # Admin xem tất cả; Seller chỉ xem đơn của store mình
            if 'Admin' not in roles:
                store_id = SellerOrderService._get_seller_store_id(user_id)
                if not store_id or order.store_id != store_id:
                    return {'success': False, 'message': 'Không có quyền xem lịch sử đơn hàng này'}, 403

            histories = (
                db.session.query(OrderStatusHistory, User.full_name)
                .outerjoin(User, User.user_id == OrderStatusHistory.changed_by)
                .filter(OrderStatusHistory.order_id == order_id)
                .order_by(OrderStatusHistory.created_at.asc())
                .all()
            )

            history_list = [{
                'previous_status': h.prev_status,
                'new_status': h.new_status,
                'changed_by_name': full_name,
                'change_note': h.note,
                'created_at': h.created_at.isoformat() if h.created_at else None,
            } for h, full_name in histories]

            return {
                'success': True,
                'data': {
                    'order_id': order_id,
                    'history': history_list,
                }
            }, 200

        except Exception as e:
            raise e
