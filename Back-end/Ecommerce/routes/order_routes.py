from flask import Blueprint
from controllers.order_controller import OrderController
from middlewares.auth_middleware import token_required

order_bp = Blueprint('orders', __name__, url_prefix='/api/v1')

# API 34: POST /api/v1/orders — Customer
order_bp.add_url_rule(
    '/orders',
    view_func=token_required(OrderController.place_order),
    methods=['POST']
)

# API 35: GET /api/v1/orders — Customer
order_bp.add_url_rule(
    '/orders',
    view_func=token_required(OrderController.list_my_orders),
    methods=['GET']
)

# API 36: GET /api/v1/orders/:id — Customer
order_bp.add_url_rule(
    '/orders/<int:order_id>',
    view_func=token_required(OrderController.get_order_detail),
    methods=['GET']
)

# API 37: POST /api/v1/orders/:id/cancel — Customer
order_bp.add_url_rule(
    '/orders/<int:order_id>/cancel',
    view_func=token_required(OrderController.cancel_order),
    methods=['POST']
)
