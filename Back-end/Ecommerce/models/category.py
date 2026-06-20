from extensions import db
from datetime import datetime

class Category(db.Model):
    __tablename__ = 'categories'

    category_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    parent_category_id = db.Column(db.BigInteger, nullable=True)
    category_name = db.Column(db.Unicode(150), nullable=False)
    slug = db.Column(db.Unicode(191), nullable=False)
    description = db.Column(db.Unicode(500), nullable=True)
    icon_url = db.Column(db.Unicode(500), nullable=True)
    display_order = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)