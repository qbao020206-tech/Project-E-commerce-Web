from flask import Blueprint
from controllers.store_controller import StoreController
from middlewares.auth_middleware import token_required

store_bp = Blueprint('stores', __name__, url_prefix='/api/v1')

# API 25: GET /api/v1/stores/:id — Public (không cần auth)
store_bp.add_url_rule(
    '/stores/<int:store_id>',
    view_func=StoreController.get_store_info,
    methods=['GET']
)

# API 26: GET /api/v1/seller/store — Seller (cần auth)
store_bp.add_url_rule(
    '/seller/store',
    view_func=token_required(StoreController.get_my_store),
    methods=['GET']
)

# API 27: POST /api/v1/stores — Seller (cần auth)
store_bp.add_url_rule(
    '/stores',
    view_func=token_required(StoreController.create_store),
    methods=['POST']
)

# API 28: PATCH /api/v1/seller/store — Seller (cần auth)
store_bp.add_url_rule(
    '/seller/store',
    view_func=token_required(StoreController.update_store),
    methods=['PATCH']
)
