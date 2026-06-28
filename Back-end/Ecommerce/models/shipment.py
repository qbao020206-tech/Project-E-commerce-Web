from extensions import db
from datetime import datetime


class Shipment(db.Model):
    __tablename__ = 'shipments'

    shipment_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey('orders.order_id'), nullable=False)
    # shipper_user_id: người vận chuyển được giao
    shipper_user_id = db.Column(db.BigInteger, db.ForeignKey('users.user_id'), nullable=True)
    # Tao mã vận đơn 
    tracking_code = db.Column(db.String(100), nullable=True)
    carrier = db.Column(db.Unicode(100), nullable=True)
    # shipment_status: PENDING_ASSIGNMENT → ASSIGNED → PICKED_UP → SHIPPING → DELIVERED / DELIVERY_FAILED
    shipment_status = db.Column(db.String(30), default='PENDING_ASSIGNMENT')
    # status kept for backward-compat with existing read paths (seller_order_service, order_service)
    status = db.Column(db.String(30), default='PENDING_ASSIGNMENT')
    failed_reason = db.Column(db.Unicode(500), nullable=True)
    shipping_note = db.Column(db.Unicode(500), nullable=True)
    assigned_at = db.Column(db.DateTime, nullable=True)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    shipped_at = db.Column(db.DateTime, nullable=True)   # alias for picked_up_at (kept for compat)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

