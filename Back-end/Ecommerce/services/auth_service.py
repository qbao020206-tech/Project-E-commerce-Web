import jwt
import secrets
import hashlib
import random
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, request
from extensions import db
from models.user import User, user_roles
from models.role import Role
from models.refresh_token import RefreshToken
from models.password_seset_request import PasswordResetRequest


class AuthService:

    # ─────────────────────────────────────────────
    # Helper: tạo SHA-256 hash cho refresh token
    # ─────────────────────────────────────────────
    @staticmethod
    def _hash_token(token: str) -> str:
        """Trả về SHA-256 hex digest của token (64 chars)."""
        return hashlib.sha256(token.encode()).hexdigest()

    # ─────────────────────────────────────────────
    # API 2 · Register
    # ─────────────────────────────────────────────
    @staticmethod
    def register_user(email, phone, password, full_name, gender=None, birth_date=None):
        """
        Đăng ký tài khoản mới.
        Checklist spec:
        ✅ Validate: phải có email hoặc phone
        ✅ Validate: full_name không rỗng
        ✅ Validate: password tối thiểu 6 ký tự
        ✅ Check trùng email → 409
        ✅ Check trùng phone → 409
        ✅ Hash password (werkzeug ≈ bcrypt)
        ✅ INSERT users với status='ACTIVE'
        ✅ Tự động gán role CUSTOMER
        ✅ Response 201 đúng format
        ✅ KHÔNG trả password_hash
        ✅ KHÔNG trả token (user phải gọi Login riêng)
        """

        # Validate: phải có ít nhất email hoặc phone
        if not email and not phone:
            return {"success": False, "message": "Phải cung cấp email hoặc số điện thoại"}, 400

        # Validate: full_name không rỗng
        if not full_name or not full_name.strip():
            return {"success": False, "message": "Họ tên không được để trống"}, 400

        # Validate: password tối thiểu 6 ký tự
        if not password or len(password) < 6:
            return {"success": False, "message": "Mật khẩu phải có ít nhất 6 ký tự"}, 400

        # Check trùng email (nếu có)
        if email:
            existing_email = User.query.filter(
                User.email == email,
                User.deleted_at == None
            ).first()
            if existing_email:
                return {"success": False, "message": "Email đã được sử dụng"}, 409

        # Check trùng phone (nếu có)
        if phone:
            existing_phone = User.query.filter(
                User.phone == phone,
                User.deleted_at == None
            ).first()
            if existing_phone:
                return {"success": False, "message": "Số điện thoại đã được sử dụng"}, 409

        # Hash password
        hashed_password = generate_password_hash(password)

        # Tạo user mới với status='ACTIVE'
        new_user = User(
            email=email if email else None,
            phone=phone if phone else None,
            password_hash=hashed_password,
            full_name=full_name.strip(),
            gender=gender,
            birth_date=birth_date,
            status='ACTIVE'
        )

        # Tự động gán role CUSTOMER
        customer_role = Role.query.filter_by(role_code='CUSTOMER').first()
        if not customer_role:
            customer_role = Role(
                role_code='CUSTOMER',
                role_name='Customer',
                description='Khách hàng mua sắm'
            )
            db.session.add(customer_role)
            db.session.flush()  # Lấy role_id trước khi commit

        new_user.roles.append(customer_role)

        try:
            db.session.add(new_user)
            db.session.commit()
            return {
                "success": True,
                "message": "Đăng ký thành công",
                "data": {
                    "user_id": new_user.user_id,
                    "email": new_user.email,
                    "full_name": new_user.full_name,
                    "roles": ["CUSTOMER"]
                }
            }, 201
        except Exception as e:
            db.session.rollback()
            return {"success": False, "message": str(e)}, 500

    # ─────────────────────────────────────────────
    # API 1 · Login
    # ─────────────────────────────────────────────
    @staticmethod
    def login_user(email, phone, password):
        """
        Đăng nhập và trả về access token + refresh token.
        Checklist spec:
        ✅ Validate: phải có email hoặc phone
        ✅ Validate: password không rỗng
        ✅ Query user với deleted_at IS NULL
        ✅ 401 nếu không tìm thấy user (không nói rõ cái nào sai)
        ✅ bcrypt.compare (werkzeug check_password_hash) → 401 nếu sai
        ✅ Check status='ACTIVE' → 403 'Tài khoản đã bị khóa' nếu SUSPENDED
        ✅ Tạo accessToken: JWT {user_id, roles[], email}, expires 1h
        ✅ Tạo refreshToken: random hex (KHÔNG dùng JWT)
        ✅ Lưu refresh token hash vào DB (bảng refresh_tokens)
        ✅ UPDATE last_login_at
        ✅ Response 200 đúng format
        """

        # Validate: phải có email hoặc phone
        if not email and not phone:
            return {"success": False, "message": "Phải cung cấp email hoặc số điện thoại"}, 400

        # Validate: password không rỗng
        if not password:
            return {"success": False, "message": "Mật khẩu không được để trống"}, 400

        # Query user (lọc deleted_at IS NULL)
        if email:
            user = User.query.filter(
                User.email == email,
                User.deleted_at == None
            ).first()
        else:
            user = User.query.filter(
                User.phone == phone,
                User.deleted_at == None
            ).first()

        # 401 nếu không tìm thấy hoặc sai mật khẩu (không nói rõ cái nào sai)
        if not user or not check_password_hash(user.password_hash, password):
            return {
                "success": False,
                "message": "Email/SĐT hoặc mật khẩu không đúng"
            }, 401

        # Check status ACTIVE
        if user.status != 'ACTIVE':
            return {
                "success": False,
                "message": "Tài khoản đã bị khóa"
            }, 403

        secret_key = current_app.config['JWT_SECRET_KEY']
        expires_in = 3600  # 1 giờ = 3600 giây

        # Tạo access token: JWT với payload chuẩn
        access_payload = {
            'user_id': user.user_id,
            'email': user.email,
            'roles': [role.role_code for role in user.roles],
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        access_token = jwt.encode(access_payload, secret_key, algorithm='HS256')

        # Tạo refresh token: random hex 64 bytes (KHÔNG dùng JWT)
        refresh_token_plain = secrets.token_hex(64)  # 128 hex chars
        refresh_token_hash = AuthService._hash_token(refresh_token_plain)

        # Lấy thông tin thiết bị / IP
        device_info = request.headers.get('User-Agent', '')[:500]
        ip_address = request.remote_addr

        # Lưu refresh token hash vào DB (khớp với schema bảng refresh_tokens)
        new_rt = RefreshToken(
            user_id=user.user_id,
            token_hash=refresh_token_hash,
            device_info=device_info,
            ip_address=ip_address,
            last_used_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(new_rt)

        # Cập nhật last_login_at
        user.last_login_at = datetime.utcnow()
        db.session.commit()

        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token_plain,
                "expires_in": expires_in,
                "user": {
                    "user_id": user.user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url
                }
            }
        }, 200

    # ─────────────────────────────────────────────
    # Helper: tạo JWT access token (dùng chung)
    # ─────────────────────────────────────────────
    @staticmethod
    def _create_access_token(user, secret_key, expires_in=3600):
        """Tạo JWT access token với payload chuẩn {user_id, email, roles}."""
        roles = [role.role_code for role in user.roles]
        payload = {
            'user_id': user.user_id,
            'email': user.email,
            'roles': roles,
            'exp': datetime.utcnow() + timedelta(seconds=expires_in)
        }
        return jwt.encode(payload, secret_key, algorithm='HS256')

    # ─────────────────────────────────────────────
    # API 3 · Refresh Token
    # ─────────────────────────────────────────────
    @staticmethod
    def refresh_token(refresh_token_plain):
        """
        POST /api/v1/auth/refresh-token  |  Public
        Token Rotation: revoke token cũ, tạo access token + refresh token mới.
        Steps:
        1. Validate body → 400
        2. Tính hash SHA-256
        3. Query refresh_tokens JOIN users
        4. 401 nếu không tìm thấy
        5. 401 nếu token đã bị thu hồi
        6. 401 nếu token hết hạn
        7. 403 nếu user bị khóa
        8. Tạo newAccessToken (JWT)
        9. Token Rotation: tạo refreshToken mới, revoke token cũ
        10. Response 200
        """
        # Step 1: Validate body
        if not refresh_token_plain or not refresh_token_plain.strip():
            return {"success": False, "message": "refresh_token không được để trống"}, 400

        # Step 2: Tính hash
        token_hash = AuthService._hash_token(refresh_token_plain)

        # Step 3: Query refresh_tokens JOIN users
        rt = (RefreshToken.query
              .join(User, RefreshToken.user_id == User.user_id)
              .filter(RefreshToken.token_hash == token_hash)
              .first())

        # Step 4: Không tìm thấy → 401
        if not rt:
            return {"success": False, "message": "Token không hợp lệ"}, 401

        # Step 5: Token đã bị thu hồi → 401
        if rt.revoked_at is not None:
            return {"success": False, "message": "Token đã bị thu hồi"}, 401

        # Step 6: Token hết hạn → 401
        if rt.expires_at < datetime.utcnow():
            return {"success": False, "message": "Token đã hết hạn"}, 401

        # Step 7: Check user status → 403
        user = User.query.filter(
            User.user_id == rt.user_id,
            User.deleted_at == None
        ).first()
        if not user or user.status != 'ACTIVE':
            return {"success": False, "message": "Tài khoản bị khóa"}, 403

        secret_key = current_app.config['JWT_SECRET_KEY']
        expires_in = 3600

        # Step 8: Tạo access token mới (JWT)
        new_access_token = AuthService._create_access_token(user, secret_key, expires_in)

        # Step 9: Token Rotation — tạo refresh token mới
        new_rt_plain = secrets.token_hex(64)
        new_rt_hash = AuthService._hash_token(new_rt_plain)
        device_info = request.headers.get('User-Agent', '')[:500]
        ip_address = request.remote_addr

        new_rt_record = RefreshToken(
            user_id=user.user_id,
            token_hash=new_rt_hash,
            device_info=device_info,
            ip_address=ip_address,
            last_used_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(new_rt_record)
        db.session.flush()  # Lấy refresh_token_id của bản ghi mới

        # Revoke token cũ: đánh dấu ROTATED + trỏ tới token mới
        rt.revoked_at = datetime.utcnow()
        rt.revocation_reason = 'ROTATED'
        rt.replaced_by_token_id = new_rt_record.refresh_token_id
        rt.last_used_at = datetime.utcnow()

        db.session.commit()

        return {
            "success": True,
            "data": {
                "access_token": new_access_token,
                "refresh_token": new_rt_plain,
                "expires_in": expires_in
            }
        }, 200

    # ─────────────────────────────────────────────
    # API 4 · Logout
    # ─────────────────────────────────────────────
    @staticmethod
    def logout(user_id, refresh_token_plain):
        """
        POST /api/v1/auth/logout  |  Bearer required
        Revoke refresh token của user hiện tại. Idempotent (không báo lỗi nếu không tìm thấy).
        Steps:
        1. uid từ JWT middleware (truyền vào)
        2. Validate body → 400 nếu thiếu refresh_token
        3. Tính hash SHA-256
        4. UPDATE revoked_at + revocation_reason='LOGOUT' (chỉ revoke nếu thuộc đúng user)
        5. Response 200 dù token không tồn tại (idempotent)
        """
        # Step 2: Validate
        if not refresh_token_plain or not refresh_token_plain.strip():
            return {"success": False, "message": "refresh_token không được để trống"}, 400

        # Step 3: Tính hash
        token_hash = AuthService._hash_token(refresh_token_plain)

        # Step 4: Revoke token (chỉ token chưa bị revoke, thuộc đúng user)
        rt = RefreshToken.query.filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None
        ).first()

        if rt:
            rt.revoked_at = datetime.utcnow()
            rt.revocation_reason = 'LOGOUT'
            db.session.commit()

        # Step 5: Luôn trả 200 (idempotent logout)
        return {"success": True, "message": "Đăng xuất thành công"}, 200

    # ─────────────────────────────────────────────
    # API 5 · Forgot Password — Send OTP
    # ─────────────────────────────────────────────
    @staticmethod
    def forgot_password(email, phone):
        """
        POST /api/v1/auth/forgot-password  |  Public
        Tạo OTP 6 số, lưu hash vào DB. DEMO MODE: in OTP ra console.
        Bảo mật: KHÔNG tiết lộ email/phone có tồn tại không (trả 200 dù không có user).
        """
        # Step 1: Validate phải có email hoặc phone
        if not email and not phone:
            return {"success": False, "message": "Phải cung cấp email hoặc số điện thoại"}, 400

        # Response bảo mật dùng chung (trả khi không tìm thấy user)
        safe_response = {
            "success": True,
            "message": "Nếu tài khoản tồn tại, OTP đã được gửi"
        }

        # Step 2: Tìm user (lọc deleted_at IS NULL)
        user = User.query.filter(
            ((User.email == email) if email else (User.phone == phone)),
            User.deleted_at == None
        ).first()

        # Step 3: Không tìm thấy → trả 200 (không tiết lộ)
        if not user:
            return safe_response, 200

        # Step 4: User bị khóa → 403
        if user.status == 'SUSPENDED':
            return {"success": False, "message": "Tài khoản bị khóa"}, 403

        # Step 5: Rate limit — kiểm tra request PENDING trong 5 phút gần đây
        five_min_ago = datetime.utcnow() - timedelta(minutes=5)
        recent_pending = PasswordResetRequest.query.filter(
            PasswordResetRequest.user_id == user.user_id,
            PasswordResetRequest.status == 'PENDING',
            PasswordResetRequest.created_at > five_min_ago
        ).count()
        if recent_pending > 0:
            return {
                "success": False,
                "message": "Vui lòng chờ 5 phút trước khi yêu cầu OTP mới"
            }, 429

        # Step 6: Tạo OTP 6 số
        otp = str(random.randint(100000, 999999))

        # Step 7: Hash OTP bằng SHA-256
        otp_hash = hashlib.sha256(otp.encode()).hexdigest()

        # Step 8: Mask destination
        if email:
            # a***@gmail.com (giữ ký tự đầu + domain)
            parts = email.split('@')
            masked = parts[0][0] + '***@' + parts[1] if len(parts) == 2 else email
            destination_masked = masked
            destination_display = email
        else:
            # 090***7890 (giữ 3 đầu + 2 cuối)
            destination_masked = phone[:3] + '***' + phone[-2:] if len(phone) >= 5 else phone
            destination_display = phone

        # Step 9: Hủy các request PENDING cũ của user này
        PasswordResetRequest.query.filter(
            PasswordResetRequest.user_id == user.user_id,
            PasswordResetRequest.status == 'PENDING'
        ).update({
            'status': 'CANCELLED',
            'updated_at': datetime.utcnow()
        })

        # Step 10: INSERT request mới (expires sau 5 phút)
        new_request = PasswordResetRequest(
            user_id=user.user_id,
            destination_masked=destination_masked,
            otp_hash=otp_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            status='PENDING'
        )
        db.session.add(new_request)
        db.session.commit()

        # Step 11: DEMO MODE — in OTP ra console (không gửi email thật)
        print(f"[DEMO OTP] Gửi tới {destination_display}: {otp}")

        # Step 12: Response 200
        response_data = {
            "success": True,
            "message": "Nếu tài khoản tồn tại, OTP đã được gửi",
            "data": {
                "destination_masked": destination_masked,
                "expires_in_seconds": 300
            }
        }
        # _dev_otp chỉ trả trong môi trường development
        if os.environ.get('FLASK_ENV') != 'production':
            response_data["_dev_otp"] = otp

        return response_data, 200

    # ─────────────────────────────────────────────
    # API 6 · Reset Password — Confirm OTP
    # ─────────────────────────────────────────────
    @staticmethod
    def reset_password(email, phone, otp, new_password):
        """
        POST /api/v1/auth/reset-password  |  Public
        Xác thực OTP và đổi mật khẩu. Tăng attempt_count khi sai, LOCKED khi >= max_attempts.
        Thu hồi toàn bộ refresh_tokens sau khi đổi mật khẩu thành công.
        """
        # Step 1: Validate đầu vào
        if not (email or phone) or not otp or not new_password:
            return {"success": False, "message": "Thiếu thông tin bắt buộc (email/phone, otp, new_password)"}, 400

        # Step 2: Validate new_password tối thiểu 6 ký tự
        if len(new_password) < 6:
            return {"success": False, "message": "Mật khẩu mới phải có ít nhất 6 ký tự"}, 400

        # Step 3: Tìm user (khác API 5 — trả 400 nếu không tìm thấy vì đây là action)
        user = User.query.filter(
            ((User.email == email) if email else (User.phone == phone)),
            User.deleted_at == None
        ).first()
        if not user:
            return {"success": False, "message": "Tài khoản không tồn tại"}, 400

        # Step 4: Lấy request mới nhất còn hiệu lực (PENDING hoặc VERIFIED, chưa hết hạn)
        reset_req = (PasswordResetRequest.query
                     .filter(
                         PasswordResetRequest.user_id == user.user_id,
                         PasswordResetRequest.status.in_(['PENDING', 'VERIFIED']),
                         PasswordResetRequest.expires_at > datetime.utcnow()
                     )
                     .order_by(PasswordResetRequest.created_at.desc())
                     .first())

        # Step 5: Không tìm thấy request hợp lệ → 400
        if not reset_req:
            return {"success": False, "message": "OTP không tồn tại hoặc đã hết hạn"}, 400

        # Step 6: Kiểm tra đã vượt quá số lần thử
        if reset_req.attempt_count >= reset_req.max_attempts or reset_req.status == 'LOCKED':
            return {"success": False, "message": "Đã vượt quá số lần thử"}, 429

        # Step 7: Verify OTP bằng SHA-256
        input_otp_hash = hashlib.sha256(otp.encode()).hexdigest()
        otp_correct = (input_otp_hash == reset_req.otp_hash)

        if not otp_correct:
            # Step 8: Sai OTP — tăng attempt_count, LOCKED nếu hết lượt
            reset_req.attempt_count += 1
            reset_req.updated_at = datetime.utcnow()

            if reset_req.attempt_count >= reset_req.max_attempts:
                reset_req.status = 'LOCKED'
                db.session.commit()
                return {"success": False, "message": "Tài khoản tạm khóa reset do nhập sai quá nhiều lần"}, 429

            db.session.commit()
            remaining = reset_req.max_attempts - reset_req.attempt_count
            return {
                "success": False,
                "message": f"OTP không đúng. Còn {remaining} lần thử"
            }, 400

        # Step 9: OTP đúng
        # a. Cập nhật trạng thái request → USED
        reset_req.status = 'USED'
        reset_req.verified_at = datetime.utcnow()
        reset_req.used_at = datetime.utcnow()
        reset_req.updated_at = datetime.utcnow()

        # b. Hash mật khẩu mới
        new_hash = generate_password_hash(new_password)

        # c. Cập nhật mật khẩu user
        user.password_hash = new_hash
        user.updated_at = datetime.utcnow()

        # d. Thu hồi TẤT CẢ refresh token của user (buộc đăng nhập lại)
        RefreshToken.query.filter(
            RefreshToken.user_id == user.user_id,
            RefreshToken.revoked_at == None
        ).update({
            'revoked_at': datetime.utcnow(),
            'revocation_reason': 'PASSWORD_RESET'
        })

        db.session.commit()

        # Step 10: Response 200
        return {
            "success": True,
            "message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại."
        }, 200