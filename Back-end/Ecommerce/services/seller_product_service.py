from extensions import db
from models.product import Product
from models.product_image import ProductImage
from models.store import Store
from models.user_store import UserStore
from sqlalchemy import func, and_
from datetime import datetime
from slugify import slugify
from nanoid import generate
import pytz

class SellerProductService:

    @staticmethod
    def get_seller_store(user_id):
        query = db.session.query(UserStore.store_id).filter(
            UserStore.user_id == user_id,
            UserStore.store_member_role == 'OWNER',
            UserStore.is_active == 1,
            UserStore.deleted_at.is_(None)
        ).first()
        return query[0] if query else None

    @staticmethod
    def create_product(user_id, category_id, sku, product_name, description, price, stock_quantity, image_urls):
        try:
            store_id = SellerProductService.get_seller_store(user_id)
            if not store_id:
                return {'success': False, 'message': 'Người dùng không phải chủ cửa hàng'}, 403

            existing_sku = db.session.query(Product).filter(
                Product.store_id == store_id,
                Product.sku == sku
            ).first()
            if existing_sku:
                return {'success': False, 'message': 'SKU đã tồn tại trong cửa hàng'}, 409

            slug = f"{slugify(product_name)}-{generate(size=6)}"

            utc = pytz.UTC
            now = datetime.now(utc)

            product = Product(
                store_id=store_id,
                category_id=category_id,
                sku=sku,
                product_name=product_name,
                slug=slug,
                description=description,
                price=price,
                stock_quantity=stock_quantity,
                status='ACTIVE',
                created_at=now,
                updated_at=now
            )
            db.session.add(product)
            db.session.flush()

            if image_urls:
                for idx, url in enumerate(image_urls):
                    image = ProductImage(
                        product_id=product.product_id,
                        image_url=url,
                        is_primary=(idx == 0)
                    )
                    db.session.add(image)

            store = db.session.query(Store).filter(Store.store_id == store_id).first()
            if store:
                store.total_products = (store.total_products or 0) + 1
                store.updated_at = now

            db.session.commit()

            images = []
            if image_urls:
                for idx, url in enumerate(image_urls):
                    images.append({
                        'image_url': url,
                        'is_primary': idx == 0
                    })

            return {
                'success': True,
                'data': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'slug': product.slug,
                    'price': float(product.price),
                    'stock_quantity': product.stock_quantity,
                    'status': product.status,
                    'images': images
                }
            }, 201
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_product(user_id, product_id, category_id=None, product_name=None, description=None, price=None, stock_quantity=None, status=None):
        try:
            store_id = SellerProductService.get_seller_store(user_id)
            if not store_id:
                return {'success': False, 'message': 'Người dùng không phải chủ cửa hàng'}, 403

            product = db.session.query(Product).filter(
                Product.product_id == product_id,
                Product.store_id == store_id
            ).first()

            if not product:
                return {'success': False, 'message': 'Sản phẩm không tồn tại'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            if category_id is not None:
                product.category_id = category_id
            if description is not None:
                product.description = description
            if price is not None:
                if price <= 0:
                    return {'success': False, 'message': 'Giá phải > 0'}, 400
                product.price = price
            if stock_quantity is not None:
                if stock_quantity < 0:
                    return {'success': False, 'message': 'Số lượng không được âm'}, 400
                product.stock_quantity = stock_quantity
            if status is not None:
                if status not in ['ACTIVE', 'INACTIVE']:
                    return {'success': False, 'message': 'Trạng thái không hợp lệ'}, 400
                product.status = status
            if product_name is not None:
                product.product_name = product_name
                product.slug = f"{slugify(product_name)}-{generate(size=6)}"

            product.updated_at = now
            db.session.commit()

            return {
                'success': True,
                'data': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'slug': product.slug,
                    'price': float(product.price),
                    'stock_quantity': product.stock_quantity,
                    'status': product.status
                }
            }, 200
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete_product(user_id, product_id):
        try:
            store_id = SellerProductService.get_seller_store(user_id)
            if not store_id:
                return {'success': False, 'message': 'Người dùng không phải chủ cửa hàng'}, 403

            product = db.session.query(Product).filter(
                Product.product_id == product_id,
                Product.store_id == store_id
            ).first()

            if not product:
                return {'success': False, 'message': 'Sản phẩm không tồn tại'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            product.status = 'INACTIVE'
            product.deleted_at = now
            product.updated_at = now

            store = db.session.query(Store).filter(Store.store_id == store_id).first()
            if store and store.total_products > 0:
                store.total_products -= 1
                store.updated_at = now

            db.session.commit()

            return {
                'success': True,
                'message': 'Đã ẩn sản phẩm'
            }, 200
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_seller_products(user_id, page=1, limit=20, status=None, keyword=None):
        try:
            store_id = SellerProductService.get_seller_store(user_id)
            if not store_id:
                return {'success': False, 'message': 'Người dùng không phải chủ cửa hàng'}, 403

            offset = (page - 1) * limit

            query = db.session.query(Product).filter(
                Product.store_id == store_id,
                Product.deleted_at.is_(None)
            )

            if status:
                query = query.filter(Product.status == status)

            if keyword:
                query = query.filter(Product.product_name.ilike(f'%{keyword}%'))

            total_items = query.count()
            total_pages = (total_items + limit - 1) // limit

            products = query.order_by(Product.created_at.desc()).offset(offset).limit(limit).all()

            products_list = []
            for product in products:
                images = db.session.query(ProductImage).filter(
                    ProductImage.product_id == product.product_id
                ).all()

                products_list.append({
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'slug': product.slug,
                    'price': float(product.price),
                    'stock_quantity': product.stock_quantity,
                    'status': product.status,
                    'images': [{'image_url': img.image_url, 'is_primary': img.is_primary} for img in images]
                })

            return {
                'success': True,
                'data': {
                    'products': products_list,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_items': total_items,
                        'total_pages': total_pages
                    }
                }
            }, 200
        except Exception as e:
            raise e
