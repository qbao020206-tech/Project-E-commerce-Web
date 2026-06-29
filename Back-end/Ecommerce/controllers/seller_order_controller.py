from flask import request, jsonify
from services.seller_order_service import SellerOrderService


class SellerOrderController:

    # API 38: GET /api/v1/seller/orders
    @staticmethod
    def list_store_orders(current_user):
        try:
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán mới có thể xem đơn hàng'}), 403

            status = request.args.get('status', None)
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)

            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20

            result, status_code = SellerOrderService.list_store_orders(
                user_id=current_user['user_id'],
                status=status,
                page=page,
                limit=limit
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 39: GET /api/v1/seller/orders/:id
    @staticmethod
    def get_store_order_detail(current_user, order_id):
        try:
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán mới có thể xem chi tiết đơn hàng'}), 403

            result, status_code = SellerOrderService.get_store_order_detail(
                user_id=current_user['user_id'],
                order_id=order_id
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 40: PATCH /api/v1/orders/:id/status
    @staticmethod
    def update_order_status(current_user, order_id):
        try:
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán mới có thể cập nhật trạng thái đơn hàng'}), 403

            data = request.get_json() or {}

            new_status = data.get('new_status')
            if not new_status:
                return jsonify({'success': False, 'message': 'new_status là bắt buộc'}), 400

            result, status_code = SellerOrderService.update_order_status(
                user_id=current_user['user_id'],
                order_id=order_id,
                new_status=new_status,
                change_note=data.get('change_note')
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 41: GET /api/v1/orders/:id/history — Seller hoặc Admin
    @staticmethod
    def get_order_status_history(current_user, order_id):
        try:
            roles = current_user.get('roles', [])
            if 'SELLER' not in roles and 'ADMIN' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền xem lịch sử đơn hàng'}), 403

            result, status_code = SellerOrderService.get_order_status_history(
                user_id=current_user['user_id'],
                roles=roles,
                order_id=order_id
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    @staticmethod
    def create_shipment(current_user, order_id):
        try:
            # Chỉ có role SELLER mới được phép thao tác gọi xe giao hàng
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Người bán mới được phép tạo vận đơn.'}), 403

            result, status_code = SellerOrderService.create_shipment(
                seller_id=current_user['user_id'],
                order_id=order_id
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500