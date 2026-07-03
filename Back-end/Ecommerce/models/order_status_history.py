from extensions import db
from datetime import datetime


class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_histories'

    order_status_history_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.order_id'), nullable=False)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by_user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=True)
    change_note = db.Column(db.Unicode(500), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
