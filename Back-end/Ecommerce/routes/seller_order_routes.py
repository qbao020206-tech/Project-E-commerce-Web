from flask import Blueprint
from controllers.seller_order_controller import SellerOrderController
from middlewares.auth_middleware import token_required

seller_order_bp = Blueprint('seller_orders', __name__, url_prefix='/api/v1')

# API 38: GET /api/v1/seller/orders — Seller
seller_order_bp.add_url_rule(
    '/seller/orders',
    view_func=token_required(SellerOrderController.list_store_orders),
    methods=['GET']
)

# API 39: GET /api/v1/seller/orders/:id — Seller
seller_order_bp.add_url_rule(
    '/seller/orders/<int:order_id>',
    view_func=token_required(SellerOrderController.get_store_order_detail),
    methods=['GET']
)

# API 40: PATCH /api/v1/orders/:id/status — Seller
seller_order_bp.add_url_rule(
    '/orders/<int:order_id>/status',
    view_func=token_required(SellerOrderController.update_order_status),
    methods=['PATCH']
)

# API 41: GET /api/v1/orders/:id/history — Seller hoặc Admin
seller_order_bp.add_url_rule(
    '/orders/<int:order_id>/history',
    view_func=token_required(SellerOrderController.get_order_status_history),
    methods=['GET']
)

# API: Tạo mã vận đơn (Đăng ký giao hàng qua đối tác vận chuyển)
seller_order_bp.route('/<int:order_id>/shipments', methods=['POST'])(token_required(SellerOrderController.create_shipment))