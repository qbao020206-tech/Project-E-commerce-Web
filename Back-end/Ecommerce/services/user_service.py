from extensions import db
from models.user import User
from werkzeug.security import generate_password_hash, check_password_hash

class UserService:
    
    @staticmethod
    def get_profile(user_id):
        user = User.query.get(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}, 404
        return {"status": "success",
                "message": "Lấy thông tin Profile thành công",
                
                "data":{
                    "user_id": user.user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "phone": user.phone,
                    "avatar_url": user.avatar_url,
                    "gender": user.gender,
                    "birth_date": user.birth_date,
                    "roles": [role.role_name for role in user.roles]
                }}, 200

    @staticmethod
    def update_profile(user_id, data):
        user = User.query.get(user_id)
        if not user:
            return {"status": "error", "message": "Không tìm thấy người dùng!"}, 404

        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'phone' in data:
            user.phone = data['phone']
        if 'gender' in data:
            user.gender = data['gender']
        if 'birth_date' in data:
            user.birth_date = data['birth_date']
        if 'avatar_url' in data:
            user.avatar_url = data['avatar_url']

        try:
            db.session.commit()
            return {"status": "success", "message": "Cập nhật thông tin thành công!"}, 200
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}, 500
    @staticmethod
    def change_password(user_id, old_password, new_password):
        # 1. Tìm người dùng trong DB
        user = User.query.get(user_id)
        if not user:
            return {"status": "error", "message": "Không tìm thấy người dùng!"}, 404

        # 2. Kiểm tra xem mật khẩu cũ khách nhập có đúng không?
        if not check_password_hash(user.password_hash, old_password):
            return {"status": "error", "message": "Mật khẩu cũ không chính xác!"}, 400

        # 3. Mọi thứ hợp lệ -> Băm mật khẩu mới và lưu vào DB
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()

        return {
            "status": "success", 
            "message": "Đổi mật khẩu thành công!"
        }, 200
