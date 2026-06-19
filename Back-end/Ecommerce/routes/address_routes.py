from flask import Blueprint, request
from controllers.address_controller import AddressController
from middlewares.auth_middleware import token_required

# Đã sửa lại url_prefix cho khớp với thiết kế API của em
address_bp = Blueprint('address', __name__, url_prefix='/api/v1/me/addresses')

@address_bp.route('/', methods=['GET', 'POST'], strict_slashes=False)
@token_required
def handle_addresses(current_user):
    if request.method == 'GET':
        return AddressController.get_my_addresses(current_user)
    elif request.method == 'POST':
        return AddressController.add_address(current_user)
    
# API Sửa địa chỉ HOẶC Xóa địa chỉ
@address_bp.route('/<int:address_id>', methods=['PATCH', 'PUT', 'DELETE'], strict_slashes=False)
@token_required
def update_or_delete_address(current_user, address_id):
    if request.method in ['PATCH', 'PUT']:
        return AddressController.update_address(current_user, address_id)
    elif request.method == 'DELETE':
        return AddressController.delete_address(current_user, address_id)
    
# API Đặt địa chỉ làm mặc định (Dùng PATCH)
@address_bp.route('/<int:address_id>/default', methods=['PATCH'], strict_slashes=False)
@token_required
def set_default_address(current_user, address_id):
    return AddressController.set_default_address(current_user, address_id)