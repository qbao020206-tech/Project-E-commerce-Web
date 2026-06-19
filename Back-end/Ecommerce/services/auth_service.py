import jwt
import random 
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from extensions import db
from models.user import User
from models.role import Role
from models.password_seset_request import PasswordResetRequest



class AuthService:
    
    @staticmethod
    def register_user(email, password, full_name, phone=None):
        existing_user = User.query.filter_by(email = email).first()
        if existing_user:
            return {"status": "error" , "message": "Email alredy exists"}, 400

        hashed_password = generate_password_hash(password)
        
        new_user = User(
            email=email,
            password_hash=hashed_password,
            full_name = full_name,
            phone = phone 
        )
        
        customer_role = Role.query.filter_by(role_code='CUSTOMER').first()
        if not customer_role:
            customer_role = Role(role_code='CUSTOMER', role_name='Customer', description='Khách hàng mua sắm')
            db.session.add(customer_role)
            db.session.commit()
        
        new_user.roles.append(customer_role)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return {"status": "success", "message": "User registered successfully"}, 201
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}, 500
        
    @staticmethod
    def login_user(login_id, password):
        if '@' in (login_id):
             user = User.query.filter_by(email=login_id).first()
        else:
             user = User.query.filter_by(phone=login_id).first()
        
        if not user or not check_password_hash(user.password_hash, password):
            return {"status": "error", "message": "Invalid email/phone or password"}, 401
        
        if user.status != 'ACTIVE':
            return {"status": "error", "message": "User account had been banned"}, 403
        
        secret_key = current_app.config['JWT_SECRET_KEY']
        
        access_payload = {
            'user_id': user.user_id,
            'email': user.email,
            'full_name': user.full_name,
            'roles': [role.role_code for role in user.roles],
            'exp': datetime.utcnow() + timedelta(hours=1)
        }
        
        access_token = jwt.encode(access_payload, secret_key, algorithm='HS256')
        
        refresh_payload = {
            'user_id': user.user_id,
            'exp': datetime.utcnow() + timedelta(days=7)
        }
        refresh_token = jwt.encode(refresh_payload, secret_key, algorithm='HS256')
        
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        
        return {
            "status": "success",
            "message": "Đăng nhập thành công",
            "data": {
                "user_id": user.user_id,
                "full_name": user.full_name,
                "email": user.email,
                "phone": user.phone, # Trả thêm phone về cho Frontend nếu cần
                "roles": [role.role_name for role in user.roles]
            },
            "tokens": {
                "accessToken": access_token,
                "refreshToken": refresh_token
            }
        }, 200
        
        
    @staticmethod
    def refresh_access_token(refresh_token):
        try: 
            secret_key = current_app.config['JWT_SECRET_KEY']
            payload = jwt.decode(refresh_token, secret_key, algorithms=['HS256'])
            
            user = User.query.filter_by(user_id = payload['user_id']).first()
            
            if not user or user.status != 'ACTIVE':
                return {'status':'error',
                         'message': 'Tài khoản không hợp lệ hoặc đã bị khóa'}, 401
            new_access_payload = {
                "user_id" : user.user_id,
                "email" : user.email,
                "full_name" : user.full_name,
                "roles" : [role.role_name for role in user.roles ],
                "exp" : datetime.utcnow() + timedelta(hours=1)
            }
            new_access_token = jwt.encode(new_access_payload, secret_key, algorithm='HS256')

            return {"status": "success",
                     "message": "Làm mới token thành công",
                     "data":{
                         "access_token": new_access_token} }, 200
            
        except jwt.ExpiredSignatureError:
            return {"status": "error", "message": "Phiên đăng nhập đã hết hạn hoàn toàn. Vui lòng đăng nhập lại!"}, 401
        
        except jwt.InvalidTokenError:
            return {"status": "error", "message": "Refresh Token không hợp lệ hoặc bị làm giả!"}, 401

    @staticmethod
    def logout_user(token):
        try:
            secret_key = current_app.config['JWT_SECRET_KEY']
            jwt.decode(token, secret_key, algorithms=['HS256'])
            return {"status": "success", "message": "Đăng xuất thành công"}, 200
        except jwt.ExpiredSignatureError:
            return {"status": "error", "message": "Token đã hết hạn"}, 401
        except jwt.InvalidTokenError:
            return {"status": "error", "message": "Token không hợp lệ"}, 401
        
    @staticmethod
    def forgot_password(email):
        user = User.query.filter_by(email=email).first()
        if not user:
            return {"status": "error", "message": "User not found"}, 404
        
        otp = random.randint(100000, 999999)
        
        otp_hash = generate_password_hash(str(otp))
        
        try:
            name_part, domain_part = email.split('@')
            masked_email = name_part[:3] + "***@" + domain_part

        except:
            masked_email = email
        
        expiry_time = datetime.utcnow() + timedelta(minutes=5)
        new_request = PasswordResetRequest(
            user_id=user.user_id,
            destination_masked=masked_email,
            otp_hash=otp_hash,
            expires_at=expiry_time,
            status = 'PENDING'
        )
        db.session.add(new_request)
        db.session.commit()
        
        print("\n" + "="*50)
        print(f"📧 ĐANG GỬI EMAIL TỚI: {email}")
        print(f"🔑 MÃ OTP CỦA BẠN LÀ: {otp} (Hết hạn sau 5 phút)")
        print("="*50 + "\n")

        return {"status": "success", "message": "Mã OTP đã được gửi đến email của bạn!"}, 200
    
    @staticmethod
    def reset_password(email, otp_code, new_password):

        user = User.query.filter_by(email=email).first()
        if not user:
            return {"status": "error", "message": "Email không tồn tại!"}, 404

        reset_request = PasswordResetRequest.query.filter_by(
            user_id=user.user_id,
            status='PENDING'
        ).order_by(PasswordResetRequest.created_at.desc()).first()

        if not reset_request:
            return {"status": "error", "message": "Không tìm thấy yêu cầu đổi mật khẩu hợp lệ!"}, 400

        if datetime.utcnow() > reset_request.expires_at:
            reset_request.status = 'EXPIRED' # Đánh dấu là hết hạn
            db.session.commit()
            return {"status": "error", "message": "Mã OTP đã hết hạn. Vui lòng gửi lại yêu cầu!"}, 400
        if not check_password_hash(reset_request.otp_hash, str(otp_code)):
            reset_request.attempt_count += 1
            # Nếu nhập sai quá số lần cho phép -> Khóa luôn mã này
            if reset_request.attempt_count >= reset_request.max_attempts:
                reset_request.status = 'EXPIRED'
            db.session.commit()
            return {"status": "error", "message": "Mã OTP không chính xác!"}, 400

        user.password = generate_password_hash(new_password)
        
        reset_request.status = 'USED'
        reset_request.verified_at = datetime.utcnow()
        reset_request.used_at = datetime.utcnow()

        db.session.commit()

        return {"status": "success", "message": "Đổi mật khẩu thành công! Bạn có thể đăng nhập bằng mật khẩu mới."}, 200
    
        

        
        