from flask import request, jsonify
from services.cart_service import CartService


class CartController:

    # API 29: GET /api/v1/cart
    @staticmethod
    def get_my_cart(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể truy cập giỏ hàng'}), 403

            result, status_code = CartService.get_my_cart(
                customer_id=current_user['user_id']
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 30: POST /api/v1/cart/items
    @staticmethod
    def add_item(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể thêm vào giỏ hàng'}), 403

            data = request.get_json() or {}

            product_id = data.get('product_id')
            quantity = data.get('quantity')

            if not product_id or not quantity:
                return jsonify({'success': False, 'message': 'product_id và quantity là bắt buộc'}), 400

            if not isinstance(quantity, int) or quantity < 1:
                return jsonify({'success': False, 'message': 'quantity phải là số nguyên >= 1'}), 400

            result, status_code = CartService.add_item(
                customer_id=current_user['user_id'],
                product_id=product_id,
                quantity=quantity
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 31: PATCH /api/v1/cart/items/:id
    @staticmethod
    def update_item_qty(current_user, cart_item_id):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể cập nhật giỏ hàng'}), 403

            data = request.get_json() or {}
            quantity = data.get('quantity')

            if quantity is None:
                return jsonify({'success': False, 'message': 'quantity là bắt buộc'}), 400

            if not isinstance(quantity, int) or quantity < 1:
                return jsonify({'success': False, 'message': 'quantity phải là số nguyên >= 1'}), 400

            result, status_code = CartService.update_item_qty(
                customer_id=current_user['user_id'],
                cart_item_id=cart_item_id,
                quantity=quantity
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 32: DELETE /api/v1/cart/items/:id
    @staticmethod
    def remove_item(current_user, cart_item_id):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể xóa sản phẩm trong giỏ hàng'}), 403

            result, status_code = CartService.remove_item(
                customer_id=current_user['user_id'],
                cart_item_id=cart_item_id
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 33: DELETE /api/v1/cart
    @staticmethod
    def clear_cart(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể xóa giỏ hàng'}), 403

            result, status_code = CartService.clear_cart(
                customer_id=current_user['user_id']
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
