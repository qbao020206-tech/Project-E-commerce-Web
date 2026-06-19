from flask import request, jsonify 
from services.auth_service import AuthService

class AuthControllers:
    @staticmethod
    
    def register():
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        phone = data.get('phone')
        
        if not email or not password or not full_name or not phone:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        result, status_code = AuthService.register_user(email, password, full_name, phone)
        return jsonify(result), status_code
    
    @staticmethod
    def login():
        data = request.get_json()
        login_id = data.get('login_id')
        password = data.get('password')
        
        if not login_id or not password:
            return jsonify({"status": "error", "message": "Vui lòng nhập Email/Số điện thoại và Mật khẩu"}), 400
        
        result, status_code = AuthService.login_user(login_id, password)
        
        return jsonify(result), status_code
        
    