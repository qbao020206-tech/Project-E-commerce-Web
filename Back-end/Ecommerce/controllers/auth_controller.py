from flask import request, jsonify
from services.auth_service import AuthService
from middlewares.auth_middleware import token_required


class AuthControllers:

    @staticmethod
    def register():
        """
        POST /api/v1/auth/register
        Body: {email?, phone?, password, full_name, gender?, birth_date?}
        - Phải có ít nhất email hoặc phone
        - full_name không rỗng
        - password tối thiểu 6 ký tự
        """
        data = request.get_json(silent=True) or {}

        email = data.get('email', '').strip() or None
        phone = data.get('phone', '').strip() or None
        password = data.get('password', '')
        full_name = data.get('full_name', '')
        gender = data.get('gender', None)
        birth_date = data.get('birth_date', None)

        # Validate sớm ở tầng controller
        if not email and not phone:
            return jsonify({
                "success": False,
                "message": "Phải cung cấp email hoặc số điện thoại"
            }), 400

        if not full_name or not full_name.strip():
            return jsonify({
                "success": False,
                "message": "Họ tên không được để trống"
            }), 400

        if not password or len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Mật khẩu phải có ít nhất 6 ký tự"
            }), 400

        result, status_code = AuthService.register_user(
            email=email,
            phone=phone,
            password=password,
            full_name=full_name,
            gender=gender,
            birth_date=birth_date
        )
        return jsonify(result), status_code

    @staticmethod
    def login():
        """
        POST /api/v1/auth/login
        Body: {email?, phone?, password}
        - Phải có ít nhất email hoặc phone
        - password không rỗng
        """
        data = request.get_json(silent=True) or {}

        email = data.get('email', '').strip() or None
        phone = data.get('phone', '').strip() or None
        password = data.get('password', '')

        # Validate sớm ở tầng controller
        if not email and not phone:
            return jsonify({
                "success": False,
                "message": "Phải cung cấp email hoặc số điện thoại"
            }), 400

        if not password:
            return jsonify({
                "success": False,
                "message": "Mật khẩu không được để trống"
            }), 400

        result, status_code = AuthService.login_user(
            email=email,
            phone=phone,
            password=password
        )
        return jsonify(result), status_code

    @staticmethod
    def refresh_token():
        """
        POST /api/v1/auth/refresh-token  |  Public
        Body: {refresh_token}
        Đổi refresh token cũ lấy access token mới + refresh token mới (Token Rotation).
        """
        data = request.get_json(silent=True) or {}
        refresh_token_plain = data.get('refresh_token', '').strip()

        result, status_code = AuthService.refresh_token(refresh_token_plain)
        return jsonify(result), status_code

    @staticmethod
    @token_required
    def logout(current_user):
        """
        POST /api/v1/auth/logout  |  Bearer required
        Body: {refresh_token}
        Thu hồi refresh token. Idempotent — luôn trả 200.
        """
        data = request.get_json(silent=True) or {}
        refresh_token_plain = data.get('refresh_token', '').strip()

        user_id = current_user.get('user_id')
        result, status_code = AuthService.logout(user_id, refresh_token_plain)
        return jsonify(result), status_code

    @staticmethod
    def forgot_password():
        """
        POST /api/v1/auth/forgot-password  |  Public
        Body: {email?} hoặc {phone?}
        Gửi OTP 6 số (DEMO: in ra console). Không tiết lộ email/phone có tồn tại không.
        """
        data = request.get_json(silent=True) or {}

        email = data.get('email', '').strip() or None
        phone = data.get('phone', '').strip() or None

        result, status_code = AuthService.forgot_password(email=email, phone=phone)
        return jsonify(result), status_code

    @staticmethod
    def reset_password():
        """
        POST /api/v1/auth/reset-password  |  Public
        Body: {email?, phone?, otp, new_password}
        Xác thực OTP và đổi mật khẩu. Thu hồi toàn bộ refresh tokens sau khi thành công.
        """
        data = request.get_json(silent=True) or {}

        email = data.get('email', '').strip() or None
        phone = data.get('phone', '').strip() or None
        otp = data.get('otp', '').strip()
        new_password = data.get('new_password', '')

        # Validate cơ bản ở controller
        if not email and not phone:
            return jsonify({
                "success": False,
                "message": "Phải cung cấp email hoặc số điện thoại"
            }), 400

        if not otp:
            return jsonify({
                "success": False,
                "message": "OTP không được để trống"
            }), 400

        if not new_password or len(new_password) < 6:
            return jsonify({
                "success": False,
                "message": "Mật khẩu mới phải có ít nhất 6 ký tự"
            }), 400

        result, status_code = AuthService.reset_password(
            email=email,
            phone=phone,
            otp=otp,
            new_password=new_password
        )
        return jsonify(result), status_code