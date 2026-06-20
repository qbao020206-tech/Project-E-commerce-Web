from extensions import db
from models.store import Store
from models.user_store import UserStore
from models.product import Product
from sqlalchemy import func, and_
from datetime import datetime
from slugify import slugify
from nanoid import generate
import pytz


class StoreService:

    @staticmethod
    def _get_store_dict(store, total_products=None):
        """Chuyển đổi store object sang dict."""
        return {
            'store_id': store.store_id,
            'store_code': store.store_code,
            'store_name': store.store_name,
            'slug': store.slug,
            'logo_url': store.logo_url,
            'description': store.description,
            'contact_email': store.contact_email,
            'contact_phone': store.contact_phone,
            'address_line': store.address_line,
            'ward': store.ward,
            'district': store.district,
            'province': store.province,
            'total_products': total_products if total_products is not None else store.total_products,
            'status': store.status,
            'created_at': store.created_at.isoformat() if store.created_at else None,
            'updated_at': store.updated_at.isoformat() if store.updated_at else None,
        }

    # API 25: GET /api/v1/stores/:id | Public
    @staticmethod
    def get_store_info(store_id):
        try:
            # Join với products để đếm số sản phẩm đang active
            result = (
                db.session.query(Store, func.count(Product.product_id).label('product_count'))
                .outerjoin(
                    Product,
                    and_(
                        Product.store_id == Store.store_id,
                        Product.status == 'ACTIVE',
                        Product.deleted_at.is_(None)
                    )
                )
                .filter(
                    Store.store_id == store_id,
                    Store.status == 'ACTIVE',
                    Store.deleted_at.is_(None)
                )
                .group_by(Store.store_id)
                .first()
            )

            if not result:
                return {'success': False, 'message': 'Cửa hàng không tồn tại'}, 404

            store, product_count = result

            return {
                'success': True,
                'data': {
                    'store_id': store.store_id,
                    'store_name': store.store_name,
                    'slug': store.slug,
                    'logo_url': store.logo_url,
                    'description': store.description,
                    'province': store.province,
                    'contact_phone': store.contact_phone,
                    'total_products': product_count,
                    'status': store.status,
                }
            }, 200

        except Exception as e:
            raise e

    # API 26: GET /api/v1/seller/store | Seller
    @staticmethod
    def get_my_store(user_id):
        try:
            store = (
                db.session.query(Store)
                .join(UserStore, UserStore.store_id == Store.store_id)
                .filter(
                    UserStore.user_id == user_id,
                    UserStore.store_member_role == 'OWNER',
                    UserStore.is_active == 1
                )
                .first()
            )

            if not store:
                return {'success': False, 'message': 'Bạn chưa tạo shop'}, 404

            return {
                'success': True,
                'data': StoreService._get_store_dict(store)
            }, 200

        except Exception as e:
            raise e

    # API 27: POST /api/v1/stores | Seller
    @staticmethod
    def create_store(user_id, store_name, description=None, logo_url=None,
                     contact_email=None, contact_phone=None, address_line=None,
                     ward=None, district=None, province=None):
        try:
            # Kiểm tra đã có shop chưa
            existing = (
                db.session.query(UserStore)
                .filter(
                    UserStore.user_id == user_id,
                    UserStore.store_member_role == 'OWNER',
                    UserStore.is_active == 1
                )
                .first()
            )
            if existing:
                return {'success': False, 'message': 'Bạn đã có shop'}, 409

            utc = pytz.UTC
            now = datetime.now(utc)

            # Sinh store_code và slug
            store_code = 'SHOP-' + generate(size=8).upper()
            slug = slugify(store_name) + '-' + generate(size=6)

            store = Store(
                store_code=store_code,
                store_name=store_name,
                slug=slug,
                description=description,
                logo_url=logo_url,
                contact_email=contact_email,
                contact_phone=contact_phone,
                address_line=address_line,
                ward=ward,
                district=district,
                province=province,
                total_products=0,
                status='ACTIVE',
                created_at=now,
                updated_at=now
            )
            db.session.add(store)
            db.session.flush()  # Lấy store_id trước khi commit

            # Ghi vào bảng user_stores với role OWNER
            user_store = UserStore(
                user_id=user_id,
                store_id=store.store_id,
                store_member_role='OWNER',
                is_active=1,
                created_at=now,
                updated_at=now
            )
            db.session.add(user_store)
            db.session.commit()

            return {
                'success': True,
                'data': StoreService._get_store_dict(store)
            }, 201

        except Exception as e:
            db.session.rollback()
            raise e

    # API 28: PATCH /api/v1/seller/store | Seller
    @staticmethod
    def update_store(user_id, store_name=None, description=None, logo_url=None,
                     contact_email=None, contact_phone=None, address_line=None,
                     ward=None, district=None, province=None):
        try:
            store = (
                db.session.query(Store)
                .join(UserStore, UserStore.store_id == Store.store_id)
                .filter(
                    UserStore.user_id == user_id,
                    UserStore.store_member_role == 'OWNER',
                    UserStore.is_active == 1
                )
                .first()
            )

            if not store:
                return {'success': False, 'message': 'Bạn chưa tạo shop'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            # Partial update — chỉ update những trường được gửi lên
            if store_name is not None:
                store.store_name = store_name
                store.slug = slugify(store_name) + '-' + generate(size=6)
            if description is not None:
                store.description = description
            if logo_url is not None:
                store.logo_url = logo_url
            if contact_email is not None:
                store.contact_email = contact_email
            if contact_phone is not None:
                store.contact_phone = contact_phone
            if address_line is not None:
                store.address_line = address_line
            if ward is not None:
                store.ward = ward
            if district is not None:
                store.district = district
            if province is not None:
                store.province = province

            store.updated_at = now
            db.session.commit()

            return {
                'success': True,
                'data': StoreService._get_store_dict(store)
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e
