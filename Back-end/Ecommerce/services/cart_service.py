from extensions import db
from models.cart import Cart
from models.cart_item import CartItem
from models.product import Product
from models.product_image import ProductImage
from datetime import datetime
import pytz


class CartService:

    @staticmethod
    def _get_or_create_cart(customer_id):
        """Lấy giỏ hàng của user, tự động tạo mới nếu chưa có."""
        cart = db.session.query(Cart).filter(
            Cart.customer_id == customer_id
        ).first()

        if not cart:
            cart = Cart(customer_id=customer_id)
            db.session.add(cart)
            db.session.flush()  # lấy cart_id ngay

        return cart

    @staticmethod
    def _serialize_item(item, product, primary_image_url):
        """Chuyển cart_item + product thành dict, thêm flag price_changed."""
        return {
            'cart_item_id': item.cart_item_id,
            'product_id': item.product_id,
            'quantity': item.quantity,
            'price_at_added': float(item.price_at_added),
            'current_price': float(product.price),
            'price_changed': float(product.price) != float(item.price_at_added),
            'product_name': product.product_name,
            'stock_quantity': product.stock_quantity,
            'product_status': product.status,
            'primary_image': primary_image_url,
        }

    # API 29: GET /api/v1/cart
    @staticmethod
    def get_my_cart(customer_id):
        try:
            cart = CartService._get_or_create_cart(customer_id)
            db.session.commit()

            # JOIN cart_items + products + primary image
            rows = (
                db.session.query(CartItem, Product, ProductImage.image_url)
                .join(Product, Product.product_id == CartItem.product_id)
                .outerjoin(
                    ProductImage,
                    (ProductImage.product_id == CartItem.product_id) &
                    (ProductImage.is_primary == True)
                )
                .filter(CartItem.cart_id == cart.cart_id)
                .all()
            )

            items = []
            total_amount = 0.0
            has_price_change = False

            for cart_item, product, primary_image_url in rows:
                serialized = CartService._serialize_item(cart_item, product, primary_image_url)
                items.append(serialized)
                total_amount += float(product.price) * cart_item.quantity
                if serialized['price_changed']:
                    has_price_change = True

            return {
                'success': True,
                'data': {
                    'cart_id': cart.cart_id,
                    'items': items,
                    'total_amount': round(total_amount, 2),
                    'has_price_change': has_price_change,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # API 30: POST /api/v1/cart/items
    @staticmethod
    def add_item(customer_id, product_id, quantity):
        try:
            # Kiểm tra sản phẩm tồn tại và còn active
            product = db.session.query(Product).filter(
                Product.product_id == product_id,
                Product.status == 'ACTIVE',
                Product.deleted_at.is_(None)
            ).first()

            if not product:
                return {'success': False, 'message': 'Sản phẩm không tồn tại hoặc không còn bán'}, 404

            cart = CartService._get_or_create_cart(customer_id)

            # Kiểm tra item đã có trong giỏ chưa
            existing_item = db.session.query(CartItem).filter(
                CartItem.cart_id == cart.cart_id,
                CartItem.product_id == product_id
            ).first()

            if existing_item:
                # Cộng thêm số lượng, re-check stock sau cộng
                new_qty = existing_item.quantity + quantity
                if product.stock_quantity < new_qty:
                    return {
                        'success': False,
                        'message': f'Không đủ hàng trong kho. Tồn kho: {product.stock_quantity}, yêu cầu: {new_qty}'
                    }, 400

                existing_item.quantity = new_qty
                existing_item.updated_at = datetime.now(pytz.UTC)
                db.session.commit()

                return {
                    'success': True,
                    'data': {
                        'cart_item_id': existing_item.cart_item_id,
                        'product_id': existing_item.product_id,
                        'quantity': existing_item.quantity,
                        'price_at_added': float(existing_item.price_at_added),
                    }
                }, 200

            else:
                # Thêm mới — kiểm tra stock
                if product.stock_quantity < quantity:
                    return {
                        'success': False,
                        'message': f'Không đủ hàng trong kho. Tồn kho: {product.stock_quantity}'
                    }, 400

                item = CartItem(
                    cart_id=cart.cart_id,
                    product_id=product_id,
                    quantity=quantity,
                    price_at_added=product.price,
                )
                db.session.add(item)
                db.session.commit()

                return {
                    'success': True,
                    'data': {
                        'cart_item_id': item.cart_item_id,
                        'product_id': item.product_id,
                        'quantity': item.quantity,
                        'price_at_added': float(item.price_at_added),
                    }
                }, 201

        except Exception as e:
            db.session.rollback()
            raise e

    # API 31: PATCH /api/v1/cart/items/:id
    @staticmethod
    def update_item_qty(customer_id, cart_item_id, quantity):
        try:
            if quantity < 1:
                return {'success': False, 'message': 'Số lượng phải >= 1'}, 400

            # Lấy cart của user
            cart = db.session.query(Cart).filter(
                Cart.customer_id == customer_id
            ).first()

            if not cart:
                return {'success': False, 'message': 'Giỏ hàng không tồn tại'}, 404

            # Verify cart_item thuộc cart của user
            item = db.session.query(CartItem).filter(
                CartItem.cart_item_id == cart_item_id,
                CartItem.cart_id == cart.cart_id
            ).first()

            if not item:
                return {'success': False, 'message': 'Không tìm thấy sản phẩm trong giỏ hàng'}, 404

            # Kiểm tra tồn kho
            product = db.session.query(Product).filter(
                Product.product_id == item.product_id
            ).first()

            if not product or product.stock_quantity < quantity:
                stock = product.stock_quantity if product else 0
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
                    'quantity': item.quantity,
                    'price_at_added': float(item.price_at_added),
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # API 32: DELETE /api/v1/cart/items/:id
    @staticmethod
    def remove_item(customer_id, cart_item_id):
        try:
            cart = db.session.query(Cart).filter(
                Cart.customer_id == customer_id
            ).first()

            if not cart:
                return {'success': False, 'message': 'Giỏ hàng không tồn tại'}, 404

            # Verify ownership: cart_item phải thuộc cart của user
            item = db.session.query(CartItem).filter(
                CartItem.cart_item_id == cart_item_id,
                CartItem.cart_id == cart.cart_id
            ).first()

            if not item:
                return {'success': False, 'message': 'Không tìm thấy sản phẩm trong giỏ hàng'}, 404

            db.session.delete(item)
            db.session.commit()

            return {'success': True, 'message': 'Đã xóa'}, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # API 33: DELETE /api/v1/cart
    @staticmethod
    def clear_cart(customer_id):
        try:
            cart = db.session.query(Cart).filter(
                Cart.customer_id == customer_id
            ).first()

            if not cart:
                return {'success': True, 'message': 'Đã xóa giỏ hàng'}, 200

            # Xóa toàn bộ items trong giỏ
            db.session.query(CartItem).filter(
                CartItem.cart_id == cart.cart_id
            ).delete()

            db.session.commit()

            return {'success': True, 'message': 'Đã xóa giỏ hàng'}, 200

        except Exception as e:
            db.session.rollback()
            raise e
