from flask import request, jsonify
from services.seller_product_service import SellerProductService

class SellerProductController:

    @staticmethod
    def create_product(current_user):
        try:
            if 'Seller' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán có thể tạo sản phẩm'}), 403

            data = request.get_json()

            required_fields = ['category_id', 'sku', 'product_name', 'price']
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': 'Thiếu trường bắt buộc'}), 400

            if not isinstance(data.get('price'), (int, float)) or data['price'] <= 0:
                return jsonify({'success': False, 'message': 'Giá phải > 0'}), 400

            stock_quantity = data.get('stock_quantity', 0)
            if not isinstance(stock_quantity, int) or stock_quantity < 0:
                stock_quantity = 0

            result, status_code = SellerProductService.create_product(
                user_id=current_user['user_id'],
                category_id=data['category_id'],
                sku=data['sku'],
                product_name=data['product_name'],
                description=data.get('description'),
                price=data['price'],
                stock_quantity=stock_quantity,
                image_urls=data.get('image_urls', [])
            )

            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def update_product(current_user, product_id):
        try:
            if 'Seller' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán có thể cập nhật sản phẩm'}), 403

            data = request.get_json() or {}

            result, status_code = SellerProductService.update_product(
                user_id=current_user['user_id'],
                product_id=product_id,
                category_id=data.get('category_id'),
                product_name=data.get('product_name'),
                description=data.get('description'),
                price=data.get('price'),
                stock_quantity=data.get('stock_quantity'),
                status=data.get('status')
            )

            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def delete_product(current_user, product_id):
        try:
            if 'Seller' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán có thể xóa sản phẩm'}), 403

            result, status_code = SellerProductService.delete_product(
                user_id=current_user['user_id'],
                product_id=product_id
            )

            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_seller_products(current_user):
        try:
            if 'Seller' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán có thể xem sản phẩm của mình'}), 403

            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            status = request.args.get('status', None, type=str)
            keyword = request.args.get('keyword', None, type=str)

            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20

            result, status_code = SellerProductService.get_seller_products(
                user_id=current_user['user_id'],
                page=page,
                limit=limit,
                status=status,
                keyword=keyword
            )

            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
