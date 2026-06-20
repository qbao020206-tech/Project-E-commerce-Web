from extensions import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class Review(db.Model):
    __tablename__ = 'reviews'
    __table_args__ = (
        # Mỗi order_item chỉ được review một lần
        UniqueConstraint('order_item_id', name='UX_reviews_order_item'),
    )

    review_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.product_id'), nullable=False)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    order_item_id = db.Column(db.BigInteger, db.ForeignKey('order_items.order_item_id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Unicode(1000), nullable=True)
    status = db.Column(db.String(20), default='VISIBLE')
    hidden_by_user_id = db.Column(db.BigInteger, nullable=True)
    hidden_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = db.relationship('User', backref='reviews', foreign_keys=[customer_id])
