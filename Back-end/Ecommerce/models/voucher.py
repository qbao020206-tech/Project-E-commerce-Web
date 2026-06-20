from extensions import db
from datetime import datetime


class Voucher(db.Model):
    __tablename__ = 'vouchers'

    voucher_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    voucher_code = db.Column(db.String(50), nullable=False, unique=True)
    voucher_name = db.Column(db.Unicode(150), nullable=True)
    # store_id = NULL → platform-wide voucher (Admin only); store_id != NULL → store voucher (Seller)
    store_id = db.Column(db.BigInteger, db.ForeignKey('stores.store_id'), nullable=True)
    discount_type = db.Column(db.String(20), nullable=False)  # PERCENT | FIXED
    discount_value = db.Column(db.Numeric(18, 2), nullable=False)
    min_order_amount = db.Column(db.Numeric(18, 2), nullable=True, default=0)
    max_discount_amount = db.Column(db.Numeric(18, 2), nullable=True)
    usage_limit = db.Column(db.Integer, nullable=True)
    used_count = db.Column(db.Integer, default=0)
    # Alias kept for backward-compat with order_service (per_customer_limit)
    per_customer_limit = db.Column(db.Integer, default=1)
    usage_limit_per_customer = db.Column(db.Integer, nullable=True)
    starts_at = db.Column(db.DateTime, nullable=True)
    ends_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)


class OrderVoucher(db.Model):
    __tablename__ = 'order_vouchers'

    order_voucher_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.order_id'), nullable=False)
    voucher_id = db.Column(db.BigInteger, db.ForeignKey('vouchers.voucher_id'), nullable=False)
    discount_amount = db.Column(db.Numeric(18, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
