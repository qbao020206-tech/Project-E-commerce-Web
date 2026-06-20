from extensions import db
from datetime import datetime

class ProductImage(db.Model):
    __tablename__ = 'product_images'

    product_image_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.product_id'), nullable=False)
    image_url = db.Column(db.Unicode(500), nullable=False)
    alt_text = db.Column(db.Unicode(255), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
