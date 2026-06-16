from flask import Blueprint
from controllers.auth_controller import AuthControllers 

auth_bp = Blueprint('auth', __name__, url_prefix='/api/v1/auth')


auth_bp.add_url_rule('/register', view_func=AuthControllers.register, methods=['POST'])
auth_bp.add_url_rule('/login', view_func=AuthControllers.login, methods=['POST'])


