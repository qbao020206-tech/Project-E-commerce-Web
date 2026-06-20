from extensions import db
from models.review import Review
from models.order_item import OrderItem
from models.order import Order
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import pytz


class ReviewService:

    # API 42: POST /api/v1/reviews — Customer
    @staticmethod
    def create_review(customer_id, order_item_id, rating, comment=None):
        try:
            # Verify order_item tồn tại và thuộc đơn của customer
            order_item = db.session.query(OrderItem).filter(
                OrderItem.order_item_id == order_item_id
            ).first()

            if not order_item:
                return {'success': False, 'message': 'Mục đơn hàng không tồn tại'}, 404

            # Verify order thuộc về customer này
            order = db.session.query(Order).filter(
                Order.order_id == order_item.order_id,
                Order.customer_id == customer_id
            ).first()

            if not order:
                return {'success': False, 'message': 'Không có quyền đánh giá mục đơn hàng này'}, 403

            # Check đơn phải ở trạng thái COMPLETED
            if order.order_status != 'COMPLETED':
                return {'success': False, 'message': 'Chỉ có thể đánh giá sau khi đơn hàng đã hoàn thành'}, 400

            # Validate rating
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                return {'success': False, 'message': 'Điểm đánh giá phải từ 1 đến 5'}, 400

            utc = pytz.UTC
            now = datetime.now(utc)

            review = Review(
                product_id=order_item.product_id,
                customer_id=customer_id,
                order_item_id=order_item_id,
                rating=rating,
                comment=comment,
                status='VISIBLE',
                created_at=now,
                updated_at=now
            )
            db.session.add(review)
            db.session.commit()

            return {
                'success': True,
                'data': {
                    'review_id': review.review_id,
                    'product_id': review.product_id,
                    'rating': review.rating,
                    'comment': review.comment,
                    'created_at': review.created_at.isoformat() if review.created_at else None,
                }
            }, 201

        except IntegrityError:
            # Vi phạm UNIQUE(order_item_id) — đã đánh giá rồi
            db.session.rollback()
            return {'success': False, 'message': 'Bạn đã đánh giá sản phẩm này rồi'}, 409
        except Exception as e:
            db.session.rollback()
            raise e

    # API 43: PATCH /api/v1/reviews/:id/hide — Admin, Manager
    @staticmethod
    def hide_review(admin_user_id, review_id, reason=None):
        try:
            review = db.session.query(Review).filter(
                Review.review_id == review_id
            ).first()

            if not review:
                return {'success': False, 'message': 'Đánh giá không tồn tại'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            review.status = 'HIDDEN'
            review.hidden_by_user_id = admin_user_id
            review.hidden_at = now
            review.updated_at = now

            db.session.commit()

            return {
                'success': True,
                'data': {
                    'review_id': review.review_id,
                    'status': review.status,
                }
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e
