from extensions import db
from datetime import datetime


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    cart_item_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    cart_id = db.Column(db.BigInteger, db.ForeignKey('carts.cart_id'), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    # Giá tại thời điểm thêm vào giỏ — dùng để phát hiện thay đổi giá
    price_at_added = db.Column(db.Numeric(18, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
