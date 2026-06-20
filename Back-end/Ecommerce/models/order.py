from extensions import db
from datetime import datetime


class Order(db.Model):
    __tablename__ = 'orders'

    order_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    store_id = db.Column(db.BigInteger, db.ForeignKey('stores.store_id'), nullable=False)
    order_code = db.Column(db.String(50), nullable=False, unique=True)
    order_status = db.Column(db.String(30), nullable=False, default='PENDING')

    recipient_name = db.Column(db.Unicode(150), nullable=False)
    recipient_phone = db.Column(db.String(20), nullable=False)
    shipping_address_line = db.Column(db.Unicode(255), nullable=False)
    shipping_ward = db.Column(db.Unicode(100), nullable=True)
    shipping_district = db.Column(db.Unicode(100), nullable=True)
    shipping_province = db.Column(db.Unicode(100), nullable=False)

    payment_method = db.Column(db.String(30), nullable=False)
    customer_note = db.Column(db.Unicode(500), nullable=True)

    subtotal = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    shipping_fee = db.Column(db.Numeric(18, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(18, 2), nullable=False, default=0)

    cancelled_by_user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=True)
    cancel_reason = db.Column(db.Unicode(500), nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy='dynamic')
    status_histories = db.relationship('OrderStatusHistory', backref='order', lazy='dynamic')
