from extensions import db
from models.user import User
from models.store import Store
from models.order import Order
from models.shipment import Shipment
from models.order_status_history import OrderStatusHistory
from models.role import Role
from models.user_store import UserStore
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import pytz


class AdminService:

    # ── API 55: GET /api/v1/admin/users | Admin, Manager ─────────────────────
    @staticmethod
    def list_all_users(role_code=None, status=None, keyword=None, page=1, limit=20):
        try:
            offset = (page - 1) * limit

            # Xây dựng điều kiện WHERE động (tránh SQL injection qua parameterized query)
            filters = ["u.deleted_at IS NULL"]
            params = {'offset': offset, 'limit': limit}

            if role_code:
                filters.append("r.role_code = :role_code")
                params['role_code'] = role_code
            if status:
                filters.append("u.status = :status")
                params['status'] = status
            if keyword:
                filters.append("(u.email LIKE :kw OR u.full_name LIKE :kw)")
                params['kw'] = f'%{keyword}%'

            where_clause = ' AND '.join(filters)

            count_sql = text(f"""
                SELECT COUNT(DISTINCT u.user_id) AS total
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.user_id AND ur.status = 'ACTIVE'
                LEFT JOIN roles r ON r.role_id = ur.role_id
                WHERE {where_clause}
            """)
            total_items = db.session.execute(count_sql, params).scalar() or 0

            data_sql = text(f"""
                SELECT u.user_id, u.email, u.phone, u.full_name, u.status, u.created_at,
                       STRING_AGG(r.role_code, ',') AS roles
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.user_id AND ur.status = 'ACTIVE'
                LEFT JOIN roles r ON r.role_id = ur.role_id
                WHERE {where_clause}
                GROUP BY u.user_id, u.email, u.phone, u.full_name, u.status, u.created_at
                ORDER BY u.created_at DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """)
            rows = db.session.execute(data_sql, params).fetchall()

            users = []
            for r in rows:
                users.append({
                    'user_id': r.user_id,
                    'email': r.email,
                    'phone': r.phone,
                    'full_name': r.full_name,
                    'status': r.status,
                    'roles': r.roles.split(',') if r.roles else [],
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                })

            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

            return {
                'success': True,
                'data': {
                    'users': users,
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

    # ── API 56: PATCH /api/v1/admin/users/:id/status | Admin only ────────────
    @staticmethod
    def update_user_status(admin_user_id, target_user_id, status):
        try:
            VALID_STATUSES = ('ACTIVE', 'SUSPENDED')
            if status not in VALID_STATUSES:
                return {
                    'success': False,
                    'message': f'status phải là: {" hoặc ".join(VALID_STATUSES)}'
                }, 400

            # Admin không được tự khóa chính mình
            if admin_user_id == target_user_id:
                return {'success': False, 'message': 'Không thể thay đổi trạng thái tài khoản của chính mình'}, 400

            user = db.session.query(User).filter(
                User.user_id == target_user_id,
                User.deleted_at.is_(None)
            ).first()
            if not user:
                return {'success': False, 'message': 'Người dùng không tồn tại'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            user.status = status
            user.updated_at = now
            db.session.commit()

            return {
                'success': True,
                'data': {
                    'user_id': user.user_id,
                    'status': user.status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # ── API 57: POST /api/v1/admin/users/:id/roles | Admin only ──────────────
    @staticmethod
    def assign_role(admin_user_id, target_user_id, role_code):
        try:
            # Check user tồn tại
            user = db.session.query(User).filter(
                User.user_id == target_user_id,
                User.deleted_at.is_(None)
            ).first()
            if not user:
                return {'success': False, 'message': 'Người dùng không tồn tại'}, 404

            # Check role tồn tại
            role = db.session.query(Role).filter(
                Role.role_code == role_code,
                Role.status == 'ACTIVE'
            ).first()
            if not role:
                return {'success': False, 'message': f'Role "{role_code}" không tồn tại'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            # INSERT vào user_roles — UX_user_roles_user_role sẽ bắt duplicate
            insert_sql = text("""
                INSERT INTO user_roles
                    (user_id, role_id, assigned_by_user_id, status, assigned_at, created_at, updated_at)
                VALUES
                    (:user_id, :role_id, :assigned_by, 'ACTIVE', :now, :now, :now)
            """)
            db.session.execute(insert_sql, {
                'user_id': target_user_id,
                'role_id': role.role_id,
                'assigned_by': admin_user_id,
                'now': now
            })
            db.session.commit()

            return {
                'success': True,
                'data': {
                    'user_id': target_user_id,
                    'role_code': role.role_code,
                }
            }, 201

        except IntegrityError:
            db.session.rollback()
            return {'success': False, 'message': 'Người dùng đã có role này rồi'}, 409
        except Exception as e:
            db.session.rollback()
            raise e

    # ── API 58: GET /api/v1/admin/stores | Admin, Manager ────────────────────
    @staticmethod
    def list_all_stores(status=None, keyword=None, page=1, limit=20):
        try:
            offset = (page - 1) * limit

            filters = ["s.deleted_at IS NULL"]
            params = {'offset': offset, 'limit': limit}

            if status:
                filters.append("s.status = :status")
                params['status'] = status
            if keyword:
                filters.append("s.store_name LIKE :kw")
                params['kw'] = f'%{keyword}%'

            where_clause = ' AND '.join(filters)

            count_sql = text(f"""
                SELECT COUNT(*) AS total
                FROM stores s
                JOIN user_stores us ON us.store_id = s.store_id
                    AND us.store_member_role = 'OWNER' AND us.is_active = 1
                JOIN users u ON us.user_id = u.user_id
                WHERE {where_clause}
            """)
            total_items = db.session.execute(count_sql, params).scalar() or 0

            data_sql = text(f"""
                SELECT s.store_id, s.store_name, s.slug, s.status,
                       s.total_products, s.created_at, s.logo_url,
                       u.full_name AS owner_name, u.email AS owner_email
                FROM stores s
                JOIN user_stores us ON us.store_id = s.store_id
                    AND us.store_member_role = 'OWNER' AND us.is_active = 1
                JOIN users u ON us.user_id = u.user_id
                WHERE {where_clause}
                ORDER BY s.created_at DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """)
            rows = db.session.execute(data_sql, params).fetchall()

            stores = []
            for r in rows:
                stores.append({
                    'store_id': r.store_id,
                    'store_name': r.store_name,
                    'slug': r.slug,
                    'logo_url': r.logo_url,
                    'status': r.status,
                    'total_products': r.total_products,
                    'owner_name': r.owner_name,
                    'owner_email': r.owner_email,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                })

            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

            return {
                'success': True,
                'data': {
                    'stores': stores,
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

    # ── API 59: PATCH /api/v1/admin/stores/:id/status | Admin only ───────────
    @staticmethod
    def update_store_status(store_id, status):
        try:
            VALID_STATUSES = ('ACTIVE', 'INACTIVE', 'SUSPENDED')
            if status not in VALID_STATUSES:
                return {
                    'success': False,
                    'message': f'status phải là: {", ".join(VALID_STATUSES)}'
                }, 400

            store = db.session.query(Store).filter(
                Store.store_id == store_id,
                Store.deleted_at.is_(None)
            ).first()
            if not store:
                return {'success': False, 'message': 'Cửa hàng không tồn tại'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            store.status = status
            store.updated_at = now
            db.session.commit()

            return {
                'success': True,
                'data': {
                    'store_id': store.store_id,
                    'status': store.status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # ── API 60: GET /api/v1/admin/orders | Admin, Manager ────────────────────
    @staticmethod
    def list_all_orders(status=None, store_id=None, customer_id=None,
                        from_date=None, to_date=None, page=1, limit=20):
        try:
            offset = (page - 1) * limit

            filters = ["1=1"]
            params = {'offset': offset, 'limit': limit}

            if status:
                filters.append("o.order_status = :status")
                params['status'] = status
            if store_id:
                filters.append("o.store_id = :store_id")
                params['store_id'] = store_id
            if customer_id:
                filters.append("o.customer_id = :customer_id")
                params['customer_id'] = customer_id
            if from_date:
                filters.append("o.created_at >= :from_date")
                params['from_date'] = from_date
            if to_date:
                filters.append("o.created_at <= :to_date")
                params['to_date'] = to_date

            where_clause = ' AND '.join(filters)

            count_sql = text(f"""
                SELECT COUNT(*) AS total
                FROM orders o
                JOIN users u ON o.customer_id = u.user_id
                JOIN stores s ON o.store_id = s.store_id
                WHERE {where_clause}
            """)
            total_items = db.session.execute(count_sql, params).scalar() or 0

            data_sql = text(f"""
                SELECT o.order_id, o.order_code, o.order_status, o.total_amount,
                       o.created_at, u.full_name AS customer_name, s.store_name
                FROM orders o
                JOIN users u ON o.customer_id = u.user_id
                JOIN stores s ON o.store_id = s.store_id
                WHERE {where_clause}
                ORDER BY o.created_at DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """)
            rows = db.session.execute(data_sql, params).fetchall()

            orders = []
            for r in rows:
                orders.append({
                    'order_id': r.order_id,
                    'order_code': r.order_code,
                    'order_status': r.order_status,
                    'total_amount': float(r.total_amount),
                    'customer_name': r.customer_name,
                    'store_name': r.store_name,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                })

            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

            return {
                'success': True,
                'data': {
                    'orders': orders,
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

    # ── API 61: GET /api/v1/admin/revenue | Admin, Manager ───────────────────
    @staticmethod
    def revenue_report(from_date, to_date, group_by='day', store_id=None):
        try:
            params = {'from_date': from_date, 'to_date': to_date}
            store_filter = ""
            if store_id:
                store_filter = "AND o.store_id = :store_id"
                params['store_id'] = store_id

            if group_by == 'store':
                data_sql = text(f"""
                    SELECT s.store_name AS label,
                           COUNT(*) AS order_count,
                           SUM(o.total_amount) AS revenue
                    FROM orders o
                    JOIN stores s ON o.store_id = s.store_id
                    WHERE o.order_status = 'COMPLETED'
                      AND o.created_at BETWEEN :from_date AND :to_date
                      {store_filter}
                    GROUP BY o.store_id, s.store_name
                    ORDER BY revenue DESC
                """)
            else:  # default: day
                data_sql = text(f"""
                    SELECT CAST(o.created_at AS DATE) AS label,
                           COUNT(*) AS order_count,
                           SUM(o.total_amount) AS revenue
                    FROM orders o
                    WHERE o.order_status = 'COMPLETED'
                      AND o.created_at BETWEEN :from_date AND :to_date
                      {store_filter}
                    GROUP BY CAST(o.created_at AS DATE)
                    ORDER BY label ASC
                """)

            rows = db.session.execute(data_sql, params).fetchall()

            data = []
            total_revenue = 0.0
            total_orders = 0

            for r in rows:
                rev = float(r.revenue) if r.revenue else 0.0
                cnt = int(r.order_count) if r.order_count else 0
                total_revenue += rev
                total_orders += cnt

                label_key = 'store_name' if group_by == 'store' else 'date'
                label_val = str(r.label) if r.label else None

                data.append({
                    label_key: label_val,
                    'order_count': cnt,
                    'revenue': rev,
                })

            return {
                'success': True,
                'data': {
                    'from_date': str(from_date),
                    'to_date': str(to_date),
                    'group_by': group_by,
                    'total_revenue': round(total_revenue, 2),
                    'total_orders': total_orders,
                    'data': data,
                }
            }, 200

        except Exception as e:
            raise e

    # ── API 62: POST /api/v1/admin/shipments/:orderId/assign | Admin only ─────
    @staticmethod
    def assign_shipper(order_id, shipper_user_id):
        try:
            # Check order tồn tại và đang READY_TO_SHIP
            order = db.session.query(Order).filter(
                Order.order_id == order_id,
                Order.deleted_at.is_(None)
            ).first()
            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404

            if order.order_status != 'READY_TO_SHIP':
                return {
                    'success': False,
                    'message': f'Đơn hàng phải ở trạng thái READY_TO_SHIP (hiện tại: {order.order_status})'
                }, 400

            # Check shipper tồn tại và có role SHIPPER
            check_sql = text("""
                SELECT u.user_id
                FROM users u
                JOIN user_roles ur ON ur.user_id = u.user_id AND ur.status = 'ACTIVE'
                JOIN roles r ON r.role_id = ur.role_id AND r.role_code = 'Shipper'
                WHERE u.user_id = :sid AND u.deleted_at IS NULL
            """)
            shipper_row = db.session.execute(check_sql, {'sid': shipper_user_id}).fetchone()
            if not shipper_row:
                return {
                    'success': False,
                    'message': 'Người dùng không tồn tại hoặc không có role Shipper'
                }, 400

            # Lấy shipment đã được tạo khi seller chuyển sang READY_TO_SHIP (API 40)
            shipment = db.session.query(Shipment).filter(
                Shipment.order_id == order_id
            ).first()
            if not shipment:
                return {'success': False, 'message': 'Chưa có shipment cho đơn hàng này'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            shipment.shipper_user_id = shipper_user_id
            shipment.shipment_status = 'ASSIGNED'
            shipment.status = 'ASSIGNED'  # backward-compat
            shipment.assigned_at = now
            shipment.updated_at = now

            db.session.commit()

            return {
                'success': True,
                'data': {
                    'shipment_id': shipment.shipment_id,
                    'shipper_user_id': shipment.shipper_user_id,
                    'shipment_status': shipment.shipment_status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e
