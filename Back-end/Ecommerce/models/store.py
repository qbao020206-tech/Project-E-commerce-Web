from extensions import db
from datetime import datetime

class Store(db.Model):
    __tablename__ = 'stores'

    store_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    store_code = db.Column(db.String(30), nullable=False, unique=True)
    store_name = db.Column(db.Unicode(150), nullable=False)
    slug = db.Column(db.Unicode(191), nullable=False, unique=True)
    description = db.Column(db.Unicode, nullable=True)
    logo_url = db.Column(db.Unicode(500), nullable=True)
    contact_email = db.Column(db.Unicode(255), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)
    address_line = db.Column(db.Unicode(255), nullable=True)
    ward = db.Column(db.Unicode(100), nullable=True)
    district = db.Column(db.Unicode(100), nullable=True)
    province = db.Column(db.Unicode(100), nullable=True)
    total_products = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='ACTIVE')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    products = db.relationship('Product', backref='store', lazy='dynamic')
