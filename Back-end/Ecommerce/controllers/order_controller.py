from flask import request, jsonify
from services.order_service import OrderService


class OrderController:

    # API 34: POST /api/v1/orders — Place Order
    @staticmethod
    def place_order(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể đặt hàng'}), 403

            data = request.get_json() or {}

            required_fields = ['store_id', 'items', 'recipient_name', 'recipient_phone',
                               'shipping_address_line', 'shipping_province', 'payment_method']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({'success': False, 'message': f'{field} là bắt buộc'}), 400

            items = data['items']
            if not isinstance(items, list) or len(items) == 0:
                return jsonify({'success': False, 'message': 'items phải là mảng không rỗng'}), 400

            for item in items:
                if not item.get('product_id') or not item.get('quantity'):
                    return jsonify({'success': False, 'message': 'Mỗi item cần product_id và quantity'}), 400
                if not isinstance(item['quantity'], int) or item['quantity'] < 1:
                    return jsonify({'success': False, 'message': 'quantity phải là số nguyên >= 1'}), 400

            if data['payment_method'] not in ('COD', 'BANK_TRANSFER'):
                return jsonify({'success': False, 'message': 'payment_method phải là COD hoặc BANK_TRANSFER'}), 400

            result, status_code = OrderService.place_order(
                customer_id=current_user['user_id'],
                store_id=data['store_id'],
                items=data['items'],
                recipient_name=data['recipient_name'],
                recipient_phone=data['recipient_phone'],
                shipping_address_line=data['shipping_address_line'],
                shipping_province=data['shipping_province'],
                shipping_ward=data.get('shipping_ward'),
                shipping_district=data.get('shipping_district'),
                payment_method=data['payment_method'],
                customer_note=data.get('customer_note'),
                address_id=data.get('address_id'),
                voucher_code=data.get('voucher_code'),
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 35: GET /api/v1/orders — List My Orders
    @staticmethod
    def list_my_orders(current_user):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể xem đơn hàng'}), 403

            status = request.args.get('status', None)
            page = request.args.get('page', 1, type=int)
            limit = request.args.get('limit', 20, type=int)

            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20

            result, status_code = OrderService.list_my_orders(
                customer_id=current_user['user_id'],
                status=status,
                page=page,
                limit=limit
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 36: GET /api/v1/orders/:id — Get Order Detail
    @staticmethod
    def get_order_detail(current_user, order_id):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể xem đơn hàng'}), 403

            result, status_code = OrderService.get_order_detail(
                customer_id=current_user['user_id'],
                order_id=order_id
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 37: POST /api/v1/orders/:id/cancel — Cancel Order
    @staticmethod
    def cancel_order(current_user, order_id):
        try:
            if 'CUSTOMER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể hủy đơn hàng'}), 403

            data = request.get_json() or {}

            result, status_code = OrderService.cancel_order(
                customer_id=current_user['user_id'],
                order_id=order_id,
                cancel_reason=data.get('cancel_reason')
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
