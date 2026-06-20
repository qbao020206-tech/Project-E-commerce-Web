from flask import Blueprint
from controllers.review_controller import ReviewController
from middlewares.auth_middleware import token_required

review_bp = Blueprint('reviews', __name__, url_prefix='/api/v1')

# API 42: POST /api/v1/reviews — Customer
review_bp.add_url_rule(
    '/reviews',
    view_func=token_required(ReviewController.create_review),
    methods=['POST']
)

# API 43: PATCH /api/v1/reviews/:id/hide — Admin, Manager
review_bp.add_url_rule(
    '/reviews/<int:review_id>/hide',
    view_func=token_required(ReviewController.hide_review),
    methods=['PATCH']
)
