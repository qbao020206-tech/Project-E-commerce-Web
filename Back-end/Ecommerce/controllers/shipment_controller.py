from flask import request, jsonify
from services.shipment_service import ShipmentService


class ShipmentController:

    # ── API 52: GET /api/v1/shipments/:orderId | Customer ────────────────────
    @staticmethod
    def track_shipment(current_user, order_id):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể theo dõi đơn giao'}), 403

            result, status_code = ShipmentService.track_shipment(
                order_id=order_id,
                customer_id=current_user['user_id']
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 53: GET /api/v1/shipper/shipments | Shipper ──────────────────────
    @staticmethod
    def list_assigned_shipments(current_user):
        try:
            if 'SHIPPER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ shipper mới có thể xem danh sách giao hàng'}), 403

            status = request.args.get('status', '').strip().upper() or None

            try:
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 20))
            except ValueError:
                return jsonify({'success': False, 'message': 'page và limit phải là số nguyên'}), 400

            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20

            result, status_code = ShipmentService.list_assigned_shipments(
                shipper_user_id=current_user['user_id'],
                status=status,
                page=page,
                limit=limit
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 54: PATCH /api/v1/shipper/shipments/:id/status | Shipper ─────────
    @staticmethod
    def update_shipment_status(current_user, shipment_id):
        try:
            if 'SHIPPER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ shipper mới có thể cập nhật trạng thái giao hàng'}), 403

            data = request.get_json() or {}
            new_status = data.get('new_status', '').strip().upper()
            failed_reason = data.get('failed_reason')

            if not new_status:
                return jsonify({'success': False, 'message': 'new_status là bắt buộc'}), 400

            result, status_code = ShipmentService.update_shipment_status(
                shipment_id=shipment_id,
                shipper_user_id=current_user['user_id'],
                new_status=new_status,
                failed_reason=failed_reason
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
