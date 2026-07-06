from models.cart import Cart
from extensions import db
from models.product import Product
from models.product_image import ProductImage
from models.store import Store
from models.user_store import UserStore
from models.order import Order
from models.shipment import Shipment
from services.seller_order_service import SellerOrderService
from models.order_status_history import OrderStatusHistory
from models.product_variant import ProductVariant
from models.order_item import OrderItem
from models.cart_item import CartItem
from sqlalchemy import func, and_
from datetime import datetime
from slugify import slugify
from nanoid import generate
import pytz
from utils.sku_helper import generate_sku

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
    def create_product(user_id, category_id, sku, product_name, description,
                    price, stock_quantity, image_urls, variants=None):
        try:
            store_id = SellerProductService.get_seller_store(user_id)
            if not store_id:
                return {'success': False, 'message': 'Người dùng không phải chủ cửa hàng'}, 403

            # ─── Validate variants TRƯỚC khi tạo product (fail sớm, tránh rollback) ───
            if variants:
                incoming_skus = [v.get('sku_code', '').strip() for v in variants]

                if any(not s for s in incoming_skus):
                    return {'success': False, 'message': 'Mỗi variant phải có sku_code'}, 400

                # Trùng SKU ngay trong chính request
                if len(incoming_skus) != len(set(incoming_skus)):
                    return {'success': False, 'message': 'Danh sách variants chứa SKU trùng nhau'}, 400

                # Trùng SKU với variant đã có sẵn TRONG CÙNG SHOP (không check shop khác)
                existing = db.session.query(ProductVariant.sku_code).filter(
                    ProductVariant.store_id == store_id,
                    ProductVariant.sku_code.in_(incoming_skus)
                ).all()
                if existing:
                    dup_list = ', '.join(row[0] for row in existing)
                    return {
                        'success': False,
                        'message': f'SKU đã tồn tại trong cửa hàng của bạn: {dup_list}'
                    }, 400

                for v in variants:
                    if not isinstance(v.get('price'), (int, float)) or v['price'] <= 0:
                        return {'success': False, 'message': f'Giá variant "{v["sku_code"]}" phải > 0'}, 400

            # Auto-generate SKU cho product gốc nếu seller không truyền (giữ flow cũ)
            if not sku:
                sku = generate_sku(product_name, store_id, db.session)
            else:
                existing_sku = db.session.query(Product).filter(
                    Product.store_id == store_id,
                    Product.sku == sku
                ).first()
                if existing_sku:
                    return {'success': False, 'message': f'SKU "{sku}" đã tồn tại trong cửa hàng'}, 409

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
            db.session.flush()  # lấy product_id trước khi tạo variant

            # ─── Tạo variant(s) ───
            created_variants = []
            if not variants:
                # Seller không gửi variants -> tự tạo 1 default variant từ dữ liệu product
                default_variant = ProductVariant(
                    product_id=product.product_id,
                    store_id=store_id,
                    sku_code=sku,
                    variant_name='Mặc định',
                    price=price,
                    stock_quantity=stock_quantity,
                    status='ACTIVE',
                    is_default=True,
                    created_at=now,
                    updated_at=now
                )
                db.session.add(default_variant)
                created_variants.append(default_variant)
            else:
                has_default_flag = any(v.get('is_default') for v in variants)
                for idx, v in enumerate(variants):
                    variant = ProductVariant(
                        product_id=product.product_id,
                        store_id=store_id,
                        sku_code=v['sku_code'].strip(),
                        variant_name=v.get('variant_name') or v['sku_code'],
                        option1_name=v.get('option1_name'),
                        option1_value=v.get('option1_value'),
                        option2_name=v.get('option2_name'),
                        option2_value=v.get('option2_value'),
                        price=v['price'],
                        stock_quantity=v.get('stock_quantity', 0),
                        status='ACTIVE',
                        is_default=v.get('is_default', False) if has_default_flag else (idx == 0),
                        created_at=now,
                        updated_at=now
                    )
                    db.session.add(variant)
                    created_variants.append(variant)

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

            return {
                'success': True,
                'data': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'slug': product.slug,
                    'status': product.status,
                    'variants': [{
                        'variant_id': v.variant_id,
                        'sku_code': v.sku_code,
                        'variant_name': v.variant_name,
                        'price': float(v.price),
                        'stock_quantity': v.stock_quantity,
                        'is_default': v.is_default
                    } for v in created_variants]
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

    @staticmethod
    def create_shipment(seller_id, order_id):
        try:
            # 1. KIỂM TRA ĐIỀU KIỆN (Validation)
            order = Order.query.filter_by(order_id=order_id, store_id=seller_id).first()
            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại hoặc không thuộc cửa hàng của bạn.'}, 404
            
            if order.order_status != 'CONFIRMED':
                return {'success': False, 'message': f'Chỉ được tạo vận đơn cho đơn đã xác nhận (CONFIRMED). Trạng thái hiện tại: {order.order_status}'}, 400

            # Đảm bảo đơn này chưa bị tạo trùng vận đơn trước đó
            existing_shipment = Shipment.query.filter_by(order_id=order_id).first()
            if existing_shipment:
                return {'success': False, 'message': 'Đơn hàng này đã được tạo mã vận đơn rồi!'}, 400

            # 2. GỌI API BÊN THỨ 3 (GIAO HÀNG TIẾT KIỆM - GHTK)
            # Hệ thống sẽ "nói chuyện" với GHTK để lấy mã thật
            tracking_code = SellerOrderService._call_logistics_api(order)
            
            now = datetime.utcnow()

            # 3. GHI NHẬN THỰC THỂ SHIPMENT MỚI
            new_shipment = Shipment(
                order_id=order.order_id,
                tracking_code=tracking_code,
                shipment_status='PENDING_ASSIGNMENT', # Chờ phân công tài xế
                shipping_note=order.customer_note,    # Chuyển lời nhắn của khách sang cho Shipper đọc
                created_at=now,
                updated_at=now
            )
            db.session.add(new_shipment)

            # 4. TỰ ĐỘNG CHUYỂN TRẠNG THÁI ĐƠN HÀNG (Trigger)
            order.order_status = 'READY_TO_SHIP'
            order.updated_at = now

            # 5. GHI LỊCH SỬ ĐƠN HÀNG TRACEABILITY
            history = OrderStatusHistory(
                order_id=order.order_id,
                previous_status='CONFIRMED',
                new_status='READY_TO_SHIP',
                changed_by_user_id=seller_id,
                change_note=f"Đã đăng ký vận chuyển thành công. Mã vận đơn: {tracking_code}",
                created_at=now
            )
            db.session.add(history)

            # CHỐT GIAO DỊCH DATABASE
            db.session.commit()

            return {
                'success': True,
                'message': 'Đã tạo mã vận đơn thành công.',
                'data': {
                    'order_id': order.order_id,
                    'tracking_code': tracking_code,
                    'order_status': order.order_status
                }
            }, 201  # HTTP 201: Dành riêng cho việc Create (Tạo mới) thành công

        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def _call_logistics_api(order):
        """
        HÀM GIẢ LẬP KẾT NỐI API ĐỐI TÁC VẬN CHUYỂN (GHTK / GHN)
        Em hãy trình bày hàm này cho mentor xem để chứng minh hệ thống của em có tư duy thực chiến.
        """
        import time
        import random
        import string
        
        # [THỰC TẾ DOANH NGHIỆP] - Em sẽ dùng thư viện requests để kết nối network:
        # import requests
        # payload = {
        #     "to_name": order.recipient_name,
        #     "to_phone": order.recipient_phone,
        #     "to_address": order.shipping_address_line,
        #     "weight": 500 # Tính bằng gram
        # }
        # headers = {'Token': 'API_TOKEN_GHTK'}
        # response = requests.post("https://services.ghtk.vn/services/shipment/order", json=payload, headers=headers)
        # return response.json()['order']['label']

        # [MÔ PHỎNG CHO ĐỒ ÁN MÔN HỌC] 
        # Để tránh việc lúc demo lên lớp mạng bị lag/chết, ta dùng hàm time.sleep để mô phỏng độ trễ mạng
        time.sleep(0.5) 
        
        # Sinh mã giả lập y hệt chuẩn mã của Giao Hàng Tiết Kiệm (GHTK): VD: GHTK-837492103
        random_code = ''.join(random.choices(string.digits, k=9))
        return f"GHTK-{random_code}"
    
@staticmethod
def update_item_qty(customer_id, cart_item_id, quantity):
    try:
        if quantity < 1:
            return {'success': False, 'message': 'Số lượng phải >= 1'}, 400

        cart = db.session.query(Cart).filter(
            Cart.customer_id == customer_id,
            Cart.status == 'ACTIVE'
        ).first()

        if not cart:
            return {'success': False, 'message': 'Giỏ hàng không tồn tại'}, 404

        item = db.session.query(CartItem).filter(
            CartItem.cart_item_id == cart_item_id,
            CartItem.cart_id == cart.cart_id
        ).first()

        if not item:
            return {'success': False, 'message': 'Không tìm thấy sản phẩm trong giỏ hàng'}, 404

        variant = db.session.query(ProductVariant).filter(
            ProductVariant.variant_id == item.variant_id
        ).first()

        if not variant or variant.stock_quantity < quantity:
            stock = variant.stock_quantity if variant else 0
            return {
                'success': False,
                'message': f'Không đủ hàng trong kho. Tồn kho: {stock}'
            }, 400

        item.quantity = quantity
        item.updated_at = datetime.now(pytz.UTC)
        db.session.commit()

        return {
            'success': True,
            'data': {
                'cart_item_id': item.cart_item_id,
                'product_id': item.product_id,
                'variant_id': item.variant_id,
                'quantity': item.quantity,
                'price_at_added': float(item.price_at_added),
            }
        }, 200

    except Exception as e:
        db.session.rollback()
        raise e