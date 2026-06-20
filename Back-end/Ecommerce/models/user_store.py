from extensions import db
from datetime import datetime

class UserStore(db.Model):
    __tablename__ = 'user_stores'

    user_store_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    store_id = db.Column(db.BigInteger, db.ForeignKey('stores.store_id'), nullable=False)
    store_member_role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Integer, default=1)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)
