from extensions import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class Conversation(db.Model):
    __tablename__ = 'conversations'
    __table_args__ = (
        # Mỗi cặp customer-store chỉ có 1 conversation (có thể kèm order_id)
        UniqueConstraint('customer_id', 'store_id', name='UX_conversations_customer_store'),
    )

    conversation_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    customer_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    store_id = db.Column(db.BigInteger, db.ForeignKey('stores.store_id'), nullable=False)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.order_id'), nullable=True)
    status = db.Column(db.String(20), default='OPEN')
    last_message_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = db.relationship('Message', backref='conversation', lazy='dynamic')
