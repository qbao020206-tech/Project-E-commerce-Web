from flask import request, jsonify
from services.review_service import ReviewService


class ReviewController:

    # API 42: POST /api/v1/reviews — Customer
    @staticmethod
    def create_review(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể đánh giá sản phẩm'}), 403

            data = request.get_json() or {}

            order_item_id = data.get('order_item_id')
            rating = data.get('rating')

            if not order_item_id:
                return jsonify({'success': False, 'message': 'order_item_id là bắt buộc'}), 400
            if rating is None:
                return jsonify({'success': False, 'message': 'rating là bắt buộc'}), 400
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return jsonify({'success': False, 'message': 'rating phải là số nguyên từ 1 đến 5'}), 400

            result, status_code = ReviewService.create_review(
                customer_id=current_user['user_id'],
                order_item_id=order_item_id,
                rating=rating,
                comment=data.get('comment')
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 43: PATCH /api/v1/reviews/:id/hide — Admin, Manager
    @staticmethod
    def hide_review(current_user, review_id):
        try:
            roles = current_user.get('roles', [])
            if 'ADMIN' not in roles :
                return jsonify({'success': False, 'message': 'Chỉ Admin hoặc Manager mới có thể ẩn đánh giá'}), 403

            data = request.get_json() or {}

            result, status_code = ReviewService.hide_review(
                admin_user_id=current_user['user_id'],
                review_id=review_id,
                reason=data.get('reason')
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
