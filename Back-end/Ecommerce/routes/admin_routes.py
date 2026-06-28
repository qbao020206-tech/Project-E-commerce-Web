from flask import Blueprint
from controllers.admin_controller import AdminController
from middlewares.auth_middleware import token_required

admin_bp = Blueprint('admin', __name__, url_prefix='/api/v1')

# API 55: GET /api/v1/admin/users — Admin, Manager
admin_bp.add_url_rule(
    '/admin/users',
    view_func=token_required(AdminController.list_all_users),
    methods=['GET']
)

# API 56: PATCH /api/v1/admin/users/:id/status — Admin only
admin_bp.add_url_rule(
    '/admin/users/<int:user_id>/status',
    view_func=token_required(AdminController.update_user_status),
    methods=['PATCH']
)

# API 57: POST /api/v1/admin/users/:id/roles — Admin only
admin_bp.add_url_rule(
    '/admin/users/<int:user_id>/roles',
    view_func=token_required(AdminController.assign_role),
    methods=['POST']
)

# API 58: GET /api/v1/admin/stores — Admin, Manager
admin_bp.add_url_rule(
    '/admin/stores',
    view_func=token_required(AdminController.list_all_stores),
    methods=['GET']
)

# API 59: PATCH /api/v1/admin/stores/:id/status — Admin only
admin_bp.add_url_rule(
    '/admin/stores/<int:store_id>/status',
    view_func=token_required(AdminController.update_store_status),
    methods=['PATCH']
)

# API 60: GET /api/v1/admin/orders — Admin, Manager
admin_bp.add_url_rule(
    '/admin/orders',
    view_func=token_required(AdminController.list_all_orders),
    methods=['GET']
)

# API 61: GET /api/v1/admin/revenue — Admin, Manager
admin_bp.add_url_rule(
    '/admin/revenue',
    view_func=token_required(AdminController.revenue_report),
    methods=['GET']
)

# API 62: POST /api/v1/admin/shipments/:orderId/assign — Admin only
admin_bp.add_url_rule(
    '/admin/shipments/<int:order_id>/assign',
    view_func=token_required(AdminController.assign_shipper),
    methods=['POST']
)

# API A: POST /api/v1/admin/roles — Admin only | Tạo role mới
admin_bp.add_url_rule(
    '/admin/roles',
    view_func=token_required(AdminController.create_role),
    methods=['POST']
)

# API B: PATCH /api/v1/admin/roles/:id — Admin only | Sửa role
admin_bp.add_url_rule(
    '/admin/roles/<int:role_id>',
    view_func=token_required(AdminController.update_role),
    methods=['PATCH']
)

# API C: DELETE /api/v1/admin/roles/:id — Admin only | Vô hiệu hóa role (soft delete)
admin_bp.add_url_rule(
    '/admin/roles/<int:role_id>',
    view_func=token_required(AdminController.delete_role),
    methods=['DELETE']
)

# API D: DELETE /api/v1/admin/users/:id/roles/:role_id — Admin only | Thu hồi role khỏi user
# ⚠ Đặt TRƯỚC route POST /admin/users/:id/roles (assign_role) để tránh Flask bắt nhầm
admin_bp.add_url_rule(
    '/admin/users/<int:user_id>/roles/<int:role_id>',
    view_func=token_required(AdminController.revoke_role),
    methods=['DELETE']
)
