from flask import Blueprint, request
from controllers.user_controller import UserController
from middlewares.auth_middleware import token_required

user_bp = Blueprint('user', __name__, url_prefix='/api/v1/users')

@user_bp.route('/me', methods=['GET', 'PATCH'])
@token_required
def user_profile(current_user):
    if request.method == 'GET':
        return UserController.get_profile(current_user)
    else:
        return UserController.update_profile(current_user)

@user_bp.route('/me/password', methods=['PATCH'])
@token_required
def user_password(current_user):
    return UserController.change_password(current_user)
    

