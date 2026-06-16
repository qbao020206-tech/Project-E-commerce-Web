import jwt
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from extensions import db
from models.user import User
from models.role import Role


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
        
        
        