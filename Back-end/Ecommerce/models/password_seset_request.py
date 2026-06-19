from extensions import db
from datetime import datetime

class PasswordResetRequest(db.Model):
    __tablename__ = 'password_reset_requests'
    
    reset_request_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    destination_masked = db.Column(db.String(255))
    otp_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    verified_at = db.Column(db.DateTime)
    used_at = db.Column(db.DateTime)
    attempt_count = db.Column(db.Integer, default=0)
    max_attempts = db.Column(db.SmallInteger, default=5)
    status = db.Column(db.String(20), default='PENDING') # PENDING, VERIFIED, USED, EXPIRED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)