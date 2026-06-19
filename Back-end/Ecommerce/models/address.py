from extensions import db
from datetime import datetime

class Address(db.Model):
    __tablename__ = 'user_addresses'

    address_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    
    recipient_name = db.Column(db.Unicode(150), nullable=False) 
    recipient_phone = db.Column(db.String(20), nullable=False)
    address_line = db.Column(db.Unicode(255), nullable=False)
    ward = db.Column(db.Unicode(100), nullable=True)
    district = db.Column(db.Unicode(100), nullable=True)
    province = db.Column(db.Unicode(100), nullable=False)
    country = db.Column(db.Unicode(100), nullable=False, default='Việt Nam')
    
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)