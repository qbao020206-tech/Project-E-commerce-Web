from extensions import db
from datetime import datetime


class RefreshToken(db.Model):
    """
    SQLAlchemy Model ánh xạ vào bảng 'refresh_tokens' đã có sẵn trong database.
    Cấu trúc khớp với schema thực tế trên SQL Server.
    """
    __tablename__ = 'refresh_tokens'

    refresh_token_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    token_hash = db.Column(db.String(255), nullable=False, unique=True)
    device_info = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    last_used_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    revocation_reason = db.Column(db.String(255), nullable=True)
    replaced_by_token_id = db.Column(db.BigInteger, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship: lấy thông tin user từ token
    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy=True))

    def is_valid(self):
        """Kiểm tra token còn hợp lệ: chưa hết hạn và chưa bị thu hồi"""
        return self.revoked_at is None and self.expires_at > datetime.utcnow()

    def __repr__(self):
        return f'<RefreshToken id={self.refresh_token_id} user_id={self.user_id}>'
