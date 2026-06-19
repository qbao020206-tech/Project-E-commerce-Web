from flask import Blueprint
from controllers.auth_controller import AuthControllers 

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


auth_bp.add_url_rule('/register', view_func=AuthControllers.register, methods=['POST'])
auth_bp.add_url_rule('/login', view_func=AuthControllers.login, methods=['POST'])
auth_bp.add_url_rule('/refresh-token', view_func=AuthControllers.refresh_token, methods=['POST'])
auth_bp.add_url_rule('/logout', view_func=AuthControllers.logout, methods=['POST'])
auth_bp.add_url_rule('/forgot-password', view_func=AuthControllers.forgot_password, methods=['POST'])
auth_bp.add_url_rule('/reset-password', view_func=AuthControllers.reset_password, methods=['POST'])



