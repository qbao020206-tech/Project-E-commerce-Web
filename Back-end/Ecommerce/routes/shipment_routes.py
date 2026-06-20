from flask import Blueprint
from controllers.shipment_controller import ShipmentController
from middlewares.auth_middleware import token_required

shipment_bp = Blueprint('shipments', __name__, url_prefix='/api/v1')

# API 52: GET /api/v1/shipments/:orderId — Customer
shipment_bp.add_url_rule(
    '/shipments/<int:order_id>',
    view_func=token_required(ShipmentController.track_shipment),
    methods=['GET']
)

# API 53: GET /api/v1/shipper/shipments — Shipper
shipment_bp.add_url_rule(
    '/shipper/shipments',
    view_func=token_required(ShipmentController.list_assigned_shipments),
    methods=['GET']
)

# API 54: PATCH /api/v1/shipper/shipments/:id/status — Shipper
shipment_bp.add_url_rule(
    '/shipper/shipments/<int:shipment_id>/status',
    view_func=token_required(ShipmentController.update_shipment_status),
    methods=['PATCH']
)
