from flask import Blueprint, request
from controllers.role_controller import RoleController
from middlewares.auth_middleware import token_required

role_bp = Blueprint('role', __name__, url_prefix='/api/v1/roles')

# API Lấy danh sách Role (Phương thức GET)
@role_bp.route('/', methods=['GET'], strict_slashes=False)
@token_required
def get_all_roles(current_user):
   return RoleController.get_all_roles(current_user)