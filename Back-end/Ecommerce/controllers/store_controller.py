from flask import request, jsonify
from services.store_service import StoreService


class StoreController:

    # API 25: GET /api/v1/stores/:id | Public
    @staticmethod
    def get_store_info(store_id):
        try:
            result, status_code = StoreService.get_store_info(store_id)
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 26: GET /api/v1/seller/store | Seller
    @staticmethod
    def get_my_store(current_user):
        try:
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán mới có thể truy cập'}), 403

            result, status_code = StoreService.get_my_store(
                user_id=current_user['user_id']
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 27: POST /api/v1/stores | Seller
    @staticmethod
    def create_store(current_user):
        try:
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán mới có thể tạo cửa hàng'}), 403

            data = request.get_json() or {}

            if not data.get('store_name'):
                return jsonify({'success': False, 'message': 'store_name là bắt buộc'}), 400

            result, status_code = StoreService.create_store(
                user_id=current_user['user_id'],
                store_name=data['store_name'],
                description=data.get('description'),
                logo_url=data.get('logo_url'),
                contact_email=data.get('contact_email'),
                contact_phone=data.get('contact_phone'),
                address_line=data.get('address_line'),
                ward=data.get('ward'),
                district=data.get('district'),
                province=data.get('province'),
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 28: PATCH /api/v1/seller/store | Seller
    @staticmethod
    def update_store(current_user):
        try:
            if 'SELLER' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ người bán mới có thể cập nhật cửa hàng'}), 403

            data = request.get_json() or {}

            result, status_code = StoreService.update_store(
                user_id=current_user['user_id'],
                store_name=data.get('store_name'),
                description=data.get('description'),
                logo_url=data.get('logo_url'),
                contact_email=data.get('contact_email'),
                contact_phone=data.get('contact_phone'),
                address_line=data.get('address_line'),
                ward=data.get('ward'),
                district=data.get('district'),
                province=data.get('province'),
            )
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
