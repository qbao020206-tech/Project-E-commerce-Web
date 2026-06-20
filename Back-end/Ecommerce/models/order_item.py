from extensions import db
from datetime import datetime


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    order_item_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.order_id'), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.product_id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(18, 2), nullable=False)
    # Snapshot tại thời điểm đặt hàng
    product_name_snapshot = db.Column(db.Unicode(200), nullable=False)
    product_image_url_snapshot = db.Column(db.Unicode(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
