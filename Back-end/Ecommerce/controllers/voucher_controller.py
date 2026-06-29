from flask import request, jsonify
from services.voucher_service import VoucherService


class VoucherController:

    # ── API 49: GET /api/v1/vouchers/check ───────────────────────────────────
    @staticmethod
    def check_voucher(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể kiểm tra voucher'}), 403

            code = request.args.get('code', '').strip()
            order_amount_raw = request.args.get('order_amount')
            store_id_raw = request.args.get('store_id')

            if not code:
                return jsonify({'success': False, 'message': 'code là bắt buộc'}), 400
            if not order_amount_raw:
                return jsonify({'success': False, 'message': 'order_amount là bắt buộc'}), 400

            try:
                order_amount = float(order_amount_raw)
            except ValueError:
                return jsonify({'success': False, 'message': 'order_amount phải là số'}), 400

            store_id = int(store_id_raw) if store_id_raw else None

            result, status_code = VoucherService.check_voucher(
                customer_id=current_user['user_id'],
                code=code,
                order_amount=order_amount,
                store_id=store_id
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 50: POST /api/v1/vouchers ────────────────────────────────────────
    @staticmethod
    def create_voucher(current_user):
        try:
            roles = current_user.get('roles', [])
            if 'ADMIN' not in roles and 'SELLER' not in roles:
                return jsonify({'success': False, 'message': 'Chỉ Admin hoặc Seller mới có thể tạo voucher'}), 403

            data = request.get_json() or {}
            result, status_code = VoucherService.create_voucher(
                user_id=current_user['user_id'],
                roles=roles,
                data=data
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 51: PATCH /api/v1/vouchers/:id ───────────────────────────────────
    @staticmethod
    def update_voucher_status(current_user, voucher_id):
        try:
            roles = current_user.get('roles', [])
            if 'ADMIN' not in roles and 'SELLER' not in roles:
                return jsonify({'success': False, 'message': 'Chỉ Admin hoặc Seller mới có thể cập nhật voucher'}), 403

            data = request.get_json() or {}
            status = data.get('status', '').strip().upper()

            if not status:
                return jsonify({'success': False, 'message': 'status là bắt buộc'}), 400

            result, status_code = VoucherService.update_voucher_status(
                user_id=current_user['user_id'],
                roles=roles,
                voucher_id=voucher_id,
                status=status
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
