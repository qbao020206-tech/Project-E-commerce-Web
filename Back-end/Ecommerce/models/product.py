from extensions import db
from datetime import datetime

class Product(db.Model):
    __tablename__ = 'products'

    product_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    store_id = db.Column(db.BigInteger, db.ForeignKey('stores.store_id'), nullable=False)
    category_id = db.Column(db.BigInteger, db.ForeignKey('categories.category_id'), nullable=False)
    sku = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.Unicode(200), nullable=False)
    slug = db.Column(db.Unicode(191), nullable=False, unique=True)
    description = db.Column(db.Unicode, nullable=True)
    price = db.Column(db.Numeric(18, 2), nullable=False)
    stock_quantity = db.Column(db.Integer, default=0)
    sold_quantity = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='ACTIVE')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    images = db.relationship('ProductImage', backref='product', lazy='dynamic')
    reviews = db.relationship('Review', backref='product', lazy='dynamic')
