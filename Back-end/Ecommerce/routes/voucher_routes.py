from flask import Blueprint
from controllers.voucher_controller import VoucherController
from middlewares.auth_middleware import token_required

voucher_bp = Blueprint('vouchers', __name__, url_prefix='/api/v1')

# API 49: GET /api/v1/vouchers/check — Customer
voucher_bp.add_url_rule(
    '/vouchers/check',
    view_func=token_required(VoucherController.check_voucher),
    methods=['GET']
)

# API 50: POST /api/v1/vouchers — Admin, Seller
voucher_bp.add_url_rule(
    '/vouchers',
    view_func=token_required(VoucherController.create_voucher),
    methods=['POST']
)

# API 51: PATCH /api/v1/vouchers/:id — Admin, Seller
voucher_bp.add_url_rule(
    '/vouchers/<int:voucher_id>',
    view_func=token_required(VoucherController.update_voucher_status),
    methods=['PATCH']
)
