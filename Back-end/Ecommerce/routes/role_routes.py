from flask import Blueprint
from controllers.role_controller import RoleController

role_bp = Blueprint('roles', __name__, url_prefix='/api/v1')

# API 15: GET /api/v1/roles — Public (không cần token)
role_bp.add_url_rule(
    '/roles',
    view_func=RoleController.get_all_roles,
    methods=['GET']
)