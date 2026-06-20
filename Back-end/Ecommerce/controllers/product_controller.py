from flask import request, jsonify
from services.product_service import ProductService

class ProductController:

    @staticmethod
    def get_products_list():
        """Lấy danh sách sản phẩm"""
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)
            keyword = request.args.get('keyword', None, type=str)
            category_id = request.args.get('category_id', None, type=int)
            store_id = request.args.get('store_id', None, type=int)
            min_price = request.args.get('min_price', None, type=float)
            max_price = request.args.get('max_price', None, type=float)
            sort_by = request.args.get('sort_by', 'created_at', type=str)
            sort_order = request.args.get('sort_order', 'DESC', type=str)

            # Validate
            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20

            # Validate sort_by
            valid_sort_by = ['price', 'sold_quantity', 'created_at']
            if sort_by not in valid_sort_by:
                sort_by = 'created_at'

            # Validate sort_order
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'

            # Validate prices
            if min_price is not None and max_price is not None:
                if max_price < min_price:
                    return jsonify({'success': False, 'message': 'max_price phải >= min_price'}), 400

            result, status_code = ProductService.get_products_list(
                page=page,
                limit=limit,
                keyword=keyword,
                category_id=category_id,
                store_id=store_id,
                min_price=min_price,
                max_price=max_price,
                sort_by=sort_by,
                sort_order=sort_order
            )

            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_product_detail(product_id):
        """Lấy chi tiết 1 sản phẩm"""
        try:
            # Validate product_id
            try:
                product_id = int(product_id)
            except ValueError:
                return jsonify({'success': False, 'message': 'product_id không hợp lệ'}), 400

            result, status_code = ProductService.get_product_detail(product_id)
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def get_product_reviews(product_id):
        """Lấy danh sách đánh giá của sản phẩm"""
        try:
            # Validate product_id
            try:
                product_id = int(product_id)
            except ValueError:
                return jsonify({'success': False, 'message': 'product_id không hợp lệ'}), 400

            # Get query parameters
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 10, type=int)
            rating = request.args.get('rating', None, type=int)
            sort_by = request.args.get('sort_by', 'created_at', type=str)
            sort_order = request.args.get('sort_order', 'DESC', type=str)

            # Validate
            if page < 1:
                page = 1
            if limit < 1 or limit > 50:
                limit = 10

            # Validate rating
            if rating is not None:
                if rating < 1 or rating > 5:
                    return jsonify({'success': False, 'message': 'rating phải từ 1 đến 5'}), 400

            # Validate sort_by
            valid_sort_by = ['created_at', 'rating']
            if sort_by not in valid_sort_by:
                sort_by = 'created_at'

            # Validate sort_order
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'

            result, status_code = ProductService.get_product_reviews(
                product_id=product_id,
                page=page,
                limit=limit,
                rating=rating,
                sort_by=sort_by,
                sort_order=sort_order
            )

            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
