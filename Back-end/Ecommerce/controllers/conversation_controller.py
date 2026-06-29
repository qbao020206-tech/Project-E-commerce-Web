from flask import request, jsonify
from services.conversation_service import ConversationService


class ConversationController:

    # ── API 44: GET /api/v1/conversations ────────────────────────────────────
    @staticmethod
    def list_conversations(current_user):
        try:
            roles = current_user.get('roles', [])
            user_id = current_user['user_id']

            # Phải là Customer hoặc Seller
            if 'CUSTOMER' not in roles and 'SELLER' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            result, status_code = ConversationService.list_conversations(user_id, roles)
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 45: POST /api/v1/conversations ───────────────────────────────────
    @staticmethod
    def create_conversation(current_user):
        try:
            roles = current_user.get('roles', [])
            if 'Customer' not in roles:
                return jsonify({'success': False, 'message': 'Chỉ khách hàng mới có thể tạo cuộc trò chuyện'}), 403

            data = request.get_json() or {}
            store_id = data.get('store_id')
            order_id = data.get('order_id')

            if not store_id:
                return jsonify({'success': False, 'message': 'store_id là bắt buộc'}), 400

            result, status_code = ConversationService.create_conversation(
                customer_id=current_user['user_id'],
                store_id=store_id,
                order_id=order_id
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 46: GET /api/v1/conversations/:id/messages ───────────────────────
    @staticmethod
    def get_messages(current_user, conversation_id):
        try:
            roles = current_user.get('roles', [])
            if 'CUSTOMER' not in roles and 'SELLER' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            try:
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 20))
            except ValueError:
                return jsonify({'success': False, 'message': 'page và limit phải là số nguyên'}), 400

            if page < 1:
                page = 1
            if limit < 1 or limit > 100:
                limit = 20

            result, status_code = ConversationService.get_messages(
                conversation_id=conversation_id,
                user_id=current_user['user_id'],
                roles=roles,
                page=page,
                limit=limit
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 47: POST /api/v1/conversations/:id/messages ──────────────────────
    @staticmethod
    def send_message(current_user, conversation_id):
        try:
            roles = current_user.get('roles', [])
            if 'CUSTOMER' not in roles and 'SELLER' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            data = request.get_json() or {}
            message_content = data.get('message_content', '')

            # Validate không rỗng / whitespace
            if not message_content or not str(message_content).strip():
                return jsonify({'success': False, 'message': 'Nội dung tin nhắn không được để trống'}), 400

            result, status_code = ConversationService.send_message(
                conversation_id=conversation_id,
                user_id=current_user['user_id'],
                roles=roles,
                message_content=message_content
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 48: PATCH /api/v1/conversations/:id/read ─────────────────────────
    @staticmethod
    def mark_as_read(current_user, conversation_id):
        try:
            roles = current_user.get('roles', [])
            if 'CUSTOMER' not in roles and 'SELLER' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            result, status_code = ConversationService.mark_as_read(
                conversation_id=conversation_id,
                user_id=current_user['user_id'],
                roles=roles
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
