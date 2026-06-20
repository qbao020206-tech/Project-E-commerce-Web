from flask import Blueprint
from controllers.cart_controller import CartController
from middlewares.auth_middleware import token_required

cart_bp = Blueprint('cart', __name__, url_prefix='/api/v1')

# API 29: GET /api/v1/cart — Customer
cart_bp.add_url_rule(
    '/cart',
    view_func=token_required(CartController.get_my_cart),
    methods=['GET']
)

# API 30: POST /api/v1/cart/items — Customer
cart_bp.add_url_rule(
    '/cart/items',
    view_func=token_required(CartController.add_item),
    methods=['POST']
)

# API 31: PATCH /api/v1/cart/items/:id — Customer
cart_bp.add_url_rule(
    '/cart/items/<int:cart_item_id>',
    view_func=token_required(CartController.update_item_qty),
    methods=['PATCH']
)

# API 32: DELETE /api/v1/cart/items/:id — Customer
cart_bp.add_url_rule(
    '/cart/items/<int:cart_item_id>',
    view_func=token_required(CartController.remove_item),
    methods=['DELETE']
)

# API 33: DELETE /api/v1/cart — Customer
cart_bp.add_url_rule(
    '/cart',
    view_func=token_required(CartController.clear_cart),
    methods=['DELETE']
)
