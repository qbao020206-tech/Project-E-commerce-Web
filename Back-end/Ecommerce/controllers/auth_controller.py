from flask import request, jsonify 
from services.auth_service import AuthService
from middlewares.auth_middleware import token_required


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
    
    @staticmethod
    def refresh_token():
        data = request.get_json()
        refresh_token = data.get('refreshToken')
        # --- THÊM 3 DÒNG NÀY ĐỂ BẮT LỖI ---
        print("\n=== TOKEN TỪ POSTMAN GỬI LÊN ===")
        print(refresh_token)
        print("================================\n")
        if not refresh_token:
            return jsonify({"status": "error", "message": "Vui lòng cung cấp Refresh Token"}), 400
        
        result, status_code = AuthService.refresh_access_token(refresh_token)
        return jsonify(result), status_code
    
    @staticmethod
    @token_required
    def logout(current_user):
        auth_header = request.headers.get('Authorization')
        token = auth_header.split()[1] if auth_header else None
        
        result, status_code = AuthService.logout_user(token)
        return jsonify(result), status_code
    
    @staticmethod
    def forgot_password():
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({"status": "error", "message": "Vui lòng cung cấp Email"}), 400
        
        result, status_code = AuthService.forgot_password(email)
        return jsonify(result), status_code
            
    @staticmethod
    def reset_password():
        data = request.get_json()
        
        email = data.get('email')
        otp_code = data.get('otpCode')
        new_password = data.get('newPassword')
       
        if not email or not otp_code or not new_password:
            return jsonify({"status": "error", "message": "Vui lòng nhập đủ Email, Mã OTP và Mật khẩu mới!"}), 400
            
        result, status_code = AuthService.reset_password(email, otp_code, new_password)
        return jsonify(result), status_code
    
    
    
    
        
        