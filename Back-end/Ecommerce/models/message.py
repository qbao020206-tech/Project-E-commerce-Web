from extensions import db
from datetime import datetime


class Message(db.Model):
    __tablename__ = 'messages'

    message_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.BigInteger, db.ForeignKey('conversations.conversation_id'), nullable=False)
    sender_user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=False)
    message_content = db.Column(db.Unicode(2000), nullable=False)
    is_read = db.Column(db.Integer, default=0)
    read_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_user_id])
