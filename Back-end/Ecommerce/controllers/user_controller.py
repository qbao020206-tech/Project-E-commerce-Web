from flask import request, jsonify 
from middlewares.auth_middleware import token_required
from services.user_service import UserService



class UserController:
    
    @staticmethod
    def get_profile(current_user):
        user_id = current_user['user_id']
        result, status_code = UserService.get_profile(user_id)
        return jsonify ({"status": "success",
                         "message": "Lấy thông tin Profile thành công", 
                         "data": current_user}), 200
    @staticmethod
    def update_profile(current_user):
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "Vui lòng cung cấp thông tin cần cập nhật!"}), 400
            
        result, status_code = UserService.update_profile(current_user['user_id'], data)
        return jsonify(result), status_code
    
    @staticmethod
    def change_password(current_user):
        data = request.get_json()
        
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')
        
        # Bắt lỗi nếu khách quên nhập
        if not old_password or not new_password:
            return jsonify({"status": "error", "message": "Vui lòng nhập đầy đủ mật khẩu cũ và mới!"}), 400
            
        result, status_code = UserService.change_password(current_user['user_id'], old_password, new_password)
        return jsonify(result), status_code
        
