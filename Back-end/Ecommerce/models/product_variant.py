from extensions import db
from datetime import datetime

class ProductVariant(db.Model):
    __tablename__ = 'product_variants'

    variant_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey('products.product_id'), nullable=False)
    store_id = db.Column(db.BigInteger, db.ForeignKey('stores.store_id'), nullable=False)
    sku_code = db.Column(db.String(50), nullable=False)
    variant_name = db.Column(db.Unicode(150), nullable=False)
    option1_name = db.Column(db.Unicode(50), nullable=True)
    option1_value = db.Column(db.Unicode(50), nullable=True)
    option2_name = db.Column(db.Unicode(50), nullable=True)
    option2_value = db.Column(db.Unicode(50), nullable=True)
    price = db.Column(db.Numeric(18, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='ACTIVE')
    is_default = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship('Product', backref='variants')