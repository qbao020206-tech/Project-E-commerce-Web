from extensions import db
from datetime import datetime


class Cart(db.Model):
    __tablename__ = 'carts'

    cart_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = db.relationship('CartItem', backref='cart', lazy='dynamic', cascade='all, delete-orphan')
