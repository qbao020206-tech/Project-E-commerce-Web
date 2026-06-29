from extensions import db
from models.voucher import Voucher, OrderVoucher
from models.order import Order
from models.user_store import UserStore
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import pytz


class VoucherService:

    # ── Helper: lấy store_id của seller (OWNER) ──────────────────────────────
    @staticmethod
    def _get_seller_store_id(user_id):
        row = (
            db.session.query(UserStore.store_id)
            .filter(
                UserStore.user_id == user_id,
                UserStore.store_member_role == 'OWNER',
                UserStore.is_active == 1
            )
            .first()
        )
        return row.store_id if row else None

    # ── Helper: chuyển voucher object → dict ─────────────────────────────────
    @staticmethod
    def _voucher_to_dict(v):
        return {
            'voucher_id': v.voucher_id,
            'voucher_code': v.voucher_code,
            'voucher_name': v.voucher_name,
            'store_id': v.store_id,
            'discount_type': v.discount_type,
            'discount_value': float(v.discount_value),
            'min_order_amount': float(v.min_order_amount) if v.min_order_amount is not None else None,
            'max_discount_amount': float(v.max_discount_amount) if v.max_discount_amount is not None else None,
            'usage_limit': v.usage_limit,
            'used_count': v.used_count,
            'usage_limit_per_customer': v.usage_limit_per_customer,
            'starts_at': v.starts_at.isoformat() if v.starts_at else None,
            'ends_at': v.ends_at.isoformat() if v.ends_at else None,
            'status': v.status,
            'created_at': v.created_at.isoformat() if v.created_at else None,
            'updated_at': v.updated_at.isoformat() if v.updated_at else None,
        }

    # ── API 49: GET /api/v1/vouchers/check ───────────────────────────────────
    @staticmethod
    def check_voucher(customer_id, code, order_amount, store_id=None):
        """
        Kiểm tra tính hợp lệ của voucher và tính discount_amount.
        Trả về {valid:True, ...} hoặc {valid:False, message:'lý do'}.
        """
        try:
            utc = pytz.UTC
            now = datetime.now(utc)

            # Tìm voucher theo code, status ACTIVE, trong thời hạn, chưa bị xóa
            sql = text("""
                SELECT *
                FROM vouchers
                WHERE voucher_code = :code
                  AND status = 'ACTIVE'
                  AND starts_at <= :now
                  AND ends_at   >= :now
                  AND deleted_at IS NULL
                  AND (store_id IS NULL OR store_id = :store_id)
            """)
            row = db.session.execute(sql, {
                'code': code,
                'now': now,
                'store_id': store_id  # NULL khi không truyền → chỉ khớp platform-wide
            }).fetchone()

            if not row:
                return {'success': True, 'data': {'valid': False, 'message': 'Voucher không tồn tại hoặc đã hết hạn'}}, 200

            # Dùng ORM để dễ xử lý logic tiếp theo
            voucher = db.session.query(Voucher).filter(
                Voucher.voucher_id == row.voucher_id
            ).first()

            # Check min_order_amount
            if voucher.min_order_amount is not None and order_amount < float(voucher.min_order_amount):
                return {
                    'success': True,
                    'data': {
                        'valid': False,
                        'message': f'Đơn hàng tối thiểu {float(voucher.min_order_amount):,.0f}đ để dùng voucher này'
                    }
                }, 200

            # Check usage_limit tổng
            if voucher.usage_limit is not None and (voucher.used_count or 0) >= voucher.usage_limit:
                return {'success': True, 'data': {'valid': False, 'message': 'Voucher đã hết lượt sử dụng'}}, 200

            # Check per-customer limit
            limit_per_cus = voucher.usage_limit_per_customer or voucher.per_customer_limit
            if limit_per_cus:
                customer_usage = (
                    db.session.query(OrderVoucher)
                    .join(Order, Order.order_id == OrderVoucher.order_id)
                    .filter(
                        OrderVoucher.voucher_id == voucher.voucher_id,
                        Order.customer_id == customer_id,
                        Order.order_status != 'CANCELLED'
                    )
                    .count()
                )
                if customer_usage >= limit_per_cus:
                    return {'success': True, 'data': {'valid': False, 'message': 'Bạn đã sử dụng hết lượt voucher này'}}, 200

            # Tính discount_amount
            if voucher.discount_type == 'PERCENT':
                discount_amount = order_amount * float(voucher.discount_value) / 100
                if voucher.max_discount_amount is not None:
                    discount_amount = min(discount_amount, float(voucher.max_discount_amount))
            else:  # FIXED
                discount_amount = min(float(voucher.discount_value), order_amount)

            return {
                'success': True,
                'data': {
                    'valid': True,
                    'voucher_code': voucher.voucher_code,
                    'voucher_name': voucher.voucher_name,
                    'discount_type': voucher.discount_type,
                    'discount_value': float(voucher.discount_value),
                    'discount_amount': round(discount_amount, 2),
                }
            }, 200

        except Exception as e:
            raise e

    # ── API 50: POST /api/v1/vouchers ────────────────────────────────────────
    @staticmethod
    def create_voucher(user_id, roles, data):
        """
        Admin: có thể tạo platform-wide (store_id=NULL) hoặc cho bất kỳ store nào.
        Seller: store_id bắt buộc và phải là store của họ.
        """
        try:
            is_admin = 'ADMIN' in roles
            is_seller = 'SELLER' in roles

            voucher_code = data.get('voucher_code', '').strip()
            voucher_name = data.get('voucher_name')
            discount_type = data.get('discount_type', '').upper()
            discount_value = data.get('discount_value')
            max_discount_amount = data.get('max_discount_amount')
            min_order_amount = data.get('min_order_amount', 0)
            usage_limit = data.get('usage_limit')
            usage_limit_per_customer = data.get('usage_limit_per_customer')
            starts_at_raw = data.get('starts_at')
            ends_at_raw = data.get('ends_at')
            store_id = data.get('store_id')

            # Validate fields bắt buộc
            if not voucher_code:
                return {'success': False, 'message': 'voucher_code là bắt buộc'}, 400
            if discount_type not in ('PERCENT', 'FIXED'):
                return {'success': False, 'message': 'discount_type phải là PERCENT hoặc FIXED'}, 400
            if discount_value is None:
                return {'success': False, 'message': 'discount_value là bắt buộc'}, 400
            try:
                discount_value = float(discount_value)
            except (TypeError, ValueError):
                return {'success': False, 'message': 'discount_value phải là số'}, 400
            if discount_type == 'PERCENT' and discount_value > 100:
                return {'success': False, 'message': 'discount_value (%) không được vượt quá 100'}, 400
            if not starts_at_raw or not ends_at_raw:
                return {'success': False, 'message': 'starts_at và ends_at là bắt buộc'}, 400

            # Parse datetime
            try:
                starts_at = datetime.fromisoformat(starts_at_raw.replace('Z', '+00:00'))
                ends_at = datetime.fromisoformat(ends_at_raw.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return {'success': False, 'message': 'Định dạng starts_at / ends_at không hợp lệ (ISO 8601)'}, 400

            if ends_at <= starts_at:
                return {'success': False, 'message': 'ends_at phải sau starts_at'}, 400

            # Phân quyền store_id
            if is_seller:
                seller_store_id = VoucherService._get_seller_store_id(user_id)
                if not seller_store_id:
                    return {'success': False, 'message': 'Bạn chưa tạo cửa hàng'}, 403
                # Seller chỉ được tạo voucher cho store của mình
                if store_id and int(store_id) != seller_store_id:
                    return {'success': False, 'message': 'Bạn không có quyền tạo voucher cho cửa hàng này'}, 403
                store_id = seller_store_id
            elif is_admin:
                # Admin: store_id=NULL → platform-wide; hoặc truyền store_id cụ thể
                store_id = int(store_id) if store_id else None

            utc = pytz.UTC
            now = datetime.now(utc)

            voucher = Voucher(
                voucher_code=voucher_code.upper(),
                voucher_name=voucher_name,
                store_id=store_id,
                discount_type=discount_type,
                discount_value=discount_value,
                min_order_amount=float(min_order_amount) if min_order_amount is not None else 0,
                max_discount_amount=float(max_discount_amount) if max_discount_amount is not None else None,
                usage_limit=int(usage_limit) if usage_limit is not None else None,
                used_count=0,
                usage_limit_per_customer=int(usage_limit_per_customer) if usage_limit_per_customer is not None else None,
                per_customer_limit=int(usage_limit_per_customer) if usage_limit_per_customer is not None else 1,
                starts_at=starts_at,
                ends_at=ends_at,
                status='ACTIVE',
                created_at=now,
                updated_at=now
            )
            db.session.add(voucher)
            db.session.commit()

            return {'success': True, 'data': VoucherService._voucher_to_dict(voucher)}, 201

        except IntegrityError:
            db.session.rollback()
            return {'success': False, 'message': 'Mã voucher đã tồn tại'}, 409
        except Exception as e:
            db.session.rollback()
            raise e

    # ── API 51: PATCH /api/v1/vouchers/:id ───────────────────────────────────
    @staticmethod
    def update_voucher_status(user_id, roles, voucher_id, status):
        """
        Seller chỉ update voucher của store mình.
        Admin update tất cả.
        """
        try:
            VALID_STATUSES = ('ACTIVE', 'INACTIVE', 'SUSPENDED')
            if status not in VALID_STATUSES:
                return {
                    'success': False,
                    'message': f'status phải là một trong: {", ".join(VALID_STATUSES)}'
                }, 400

            voucher = db.session.query(Voucher).filter(
                Voucher.voucher_id == voucher_id,
                Voucher.deleted_at.is_(None)
            ).first()

            if not voucher:
                return {'success': False, 'message': 'Voucher không tồn tại'}, 404

            is_admin = 'ADMIN' in roles
            is_seller = 'SELLER' in roles

            if is_seller and not is_admin:
                # Seller chỉ được update voucher thuộc store của mình
                seller_store_id = VoucherService._get_seller_store_id(user_id)
                if not seller_store_id or voucher.store_id != seller_store_id:
                    return {'success': False, 'message': 'Bạn không có quyền cập nhật voucher này'}, 403

            utc = pytz.UTC
            now = datetime.now(utc)

            voucher.status = status
            voucher.updated_at = now
            db.session.commit()

            return {
                'success': True,
                'data': {
                    'voucher_id': voucher.voucher_id,
                    'status': voucher.status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e
