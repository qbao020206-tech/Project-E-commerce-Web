from flask import request, jsonify
from services.address_service import AddressService
from middlewares.auth_middleware import token_required
class AddressController:
    
    @staticmethod
    def add_address(current_user):
        data = request.get_json()
        
        required_fields = ['recipient_name', 'recipient_phone', 'address_line', 'province']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"status": "error", "message": f"Vui lòng nhập đầy đủ {field}!"}), 400
                
        result, status_code = AddressService.add_address(current_user['user_id'], data)
        return jsonify(result), status_code
        
    @staticmethod
    def get_my_addresses(current_user):
        result, status_code = AddressService.get_my_addresses(current_user['user_id'])
        return jsonify(result), status_code
    
    @staticmethod
    def update_address(current_user, address_id):
        data = request.get_json()
        
        if not data:
             return jsonify({"status": "error", "message": "Vui lòng cung cấp dữ liệu cần cập nhật!"}), 400
             
        # Truyền cả user_id (từ Token) và address_id (từ URL) cho Đầu bếp
        result, status_code = AddressService.update_address(current_user['user_id'], address_id, data)
        return jsonify(result), status_code
    
    
    @staticmethod
  
    def delete_address(current_user, address_id):
        result, status_code = AddressService.delete_address(current_user['user_id'], address_id)
        return jsonify(result), status_code