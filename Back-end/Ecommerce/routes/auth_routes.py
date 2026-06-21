from flask import Blueprint
from controllers.auth_controller import AuthControllers

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')

# API 1 · Register | Public
auth_bp.add_url_rule('/register', view_func=AuthControllers.register, methods=['POST'])

# API 2 · Login | Public
auth_bp.add_url_rule('/login', view_func=AuthControllers.login, methods=['POST'])

# API 3 · Refresh Token | Public
auth_bp.add_url_rule('/refresh-token', view_func=AuthControllers.refresh_token, methods=['POST'])

# API 4 · Logout | Bearer required (token_required được áp dụng trong controller)
auth_bp.add_url_rule('/logout', view_func=AuthControllers.logout, methods=['POST'])

# API 5 · Forgot Password — Send OTP | Public
auth_bp.add_url_rule('/forgot-password', view_func=AuthControllers.forgot_password, methods=['POST'])

# API 6 · Reset Password — Confirm OTP | Public
auth_bp.add_url_rule('/reset-password', view_func=AuthControllers.reset_password, methods=['POST'])
