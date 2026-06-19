from functools import wraps
from flask import request, jsonify, current_app
import jwt

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = request.headers['Authorization'].split()
            
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify ({"status": "error",
                            "message": "Từ chối truy cập. Bạn chưa đăng nhập"}), 401
            
        try:
            secret_key = current_app.config['JWT_SECRET_KEY']
            current_user = jwt.decode(token, secret_key, algorithms=['HS256'])
            
        except jwt.ExpiredSignatureError:
            return jsonify ({"status": "error",
                            "message": "Phiên đặng nhập đã hết hạn. Vui lòng đặng nhập lại!"}), 401
            
        except jwt.InvalidTokenError:
            return jsonify ({"status": "error",
                            "message": "Đăng nhập token không hợp lệ"}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated
            