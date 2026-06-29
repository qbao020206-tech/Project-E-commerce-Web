from flask import request, jsonify
from services.admin_service import AdminService


class AdminController:

    # ── API 55: GET /api/v1/admin/users | Admin, Manager ─────────────────────
    @staticmethod
    def list_all_users(current_user):
        try:
            roles = current_user.get('roles', [])
            if 'Admin' not in roles and 'Manager' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            role_code = request.args.get('role_code', '').strip() or None
            status = request.args.get('status', '').strip().upper() or None
            keyword = request.args.get('keyword', '').strip() or None

            try:
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 20))
            except ValueError:
                return jsonify({'success': False, 'message': 'page và limit phải là số nguyên'}), 400

            if page < 1: page = 1
            if limit < 1 or limit > 100: limit = 20

            result, status_code = AdminService.list_all_users(
                role_code=role_code, status=status, keyword=keyword,
                page=page, limit=limit
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 56: PATCH /api/v1/admin/users/:id/status | Admin only ────────────
    @staticmethod
    def update_user_status(current_user, user_id):
        try:
            if 'Admin' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể thay đổi trạng thái người dùng'}), 403

            data = request.get_json() or {}
            status = data.get('status', '').strip().upper()
            if not status:
                return jsonify({'success': False, 'message': 'status là bắt buộc'}), 400

            result, status_code = AdminService.update_user_status(
                admin_user_id=current_user['user_id'],
                target_user_id=user_id,
                status=status
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 57: POST /api/v1/admin/users/:id/roles | Admin only ──────────────
    @staticmethod
    def assign_role(current_user, user_id):
        try:
            if 'Admin' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể gán role'}), 403

            data = request.get_json() or {}
            role_code = data.get('role_code', '').strip()
            if not role_code:
                return jsonify({'success': False, 'message': 'role_code là bắt buộc'}), 400

            result, status_code = AdminService.assign_role(
                admin_user_id=current_user['user_id'],
                target_user_id=user_id,
                role_code=role_code
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 58: GET /api/v1/admin/stores | Admin, Manager ────────────────────
    @staticmethod
    def list_all_stores(current_user):
        try:
            roles = current_user.get('roles', [])
            if 'Admin' not in roles and 'Manager' not in roles:
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            status = request.args.get('status', '').strip().upper() or None
            keyword = request.args.get('keyword', '').strip() or None

            try:
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 20))
            except ValueError:
                return jsonify({'success': False, 'message': 'page và limit phải là số nguyên'}), 400

            if page < 1: page = 1
            if limit < 1 or limit > 100: limit = 20

            result, status_code = AdminService.list_all_stores(
                status=status, keyword=keyword, page=page, limit=limit
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 59: PATCH /api/v1/admin/stores/:id/status | Admin only ───────────
    @staticmethod
    def update_store_status(current_user, store_id):
        try:
            if 'Admin' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể thay đổi trạng thái cửa hàng'}), 403

            data = request.get_json() or {}
            status = data.get('status', '').strip().upper()
            if not status:
                return jsonify({'success': False, 'message': 'status là bắt buộc'}), 400

            result, status_code = AdminService.update_store_status(
                store_id=store_id, status=status
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 60: GET /api/v1/admin/orders | Admin, Manager ────────────────────
    @staticmethod
    def list_all_orders(current_user):
        try:
            roles = current_user.get('roles', [])
            if 'ADMIN' not in roles :
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            status = request.args.get('status', '').strip().upper() or None
            from_date = request.args.get('from_date', '').strip() or None
            to_date = request.args.get('to_date', '').strip() or None

            store_id_raw = request.args.get('store_id')
            customer_id_raw = request.args.get('customer_id')

            try:
                store_id = int(store_id_raw) if store_id_raw else None
                customer_id = int(customer_id_raw) if customer_id_raw else None
                page = int(request.args.get('page', 1))
                limit = int(request.args.get('limit', 20))
            except ValueError:
                return jsonify({'success': False, 'message': 'Tham số số nguyên không hợp lệ'}), 400

            if page < 1: page = 1
            if limit < 1 or limit > 100: limit = 20

            result, status_code = AdminService.list_all_orders(
                status=status, store_id=store_id, customer_id=customer_id,
                from_date=from_date, to_date=to_date, page=page, limit=limit
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 61: GET /api/v1/admin/revenue | Admin, Manager ───────────────────
    @staticmethod
    def revenue_report(current_user):
        try:
            roles = current_user.get('roles', [])
            if 'ADMIN' not in roles :
                return jsonify({'success': False, 'message': 'Không có quyền truy cập'}), 403

            from_date = request.args.get('from_date', '').strip()
            to_date = request.args.get('to_date', '').strip()

            if not from_date or not to_date:
                return jsonify({'success': False, 'message': 'from_date và to_date là bắt buộc'}), 400

            group_by = request.args.get('group_by', 'day').strip().lower()
            if group_by not in ('day', 'store'):
                return jsonify({'success': False, 'message': 'group_by phải là "day" hoặc "store"'}), 400

            store_id_raw = request.args.get('store_id')
            try:
                store_id = int(store_id_raw) if store_id_raw else None
            except ValueError:
                return jsonify({'success': False, 'message': 'store_id phải là số nguyên'}), 400

            result, status_code = AdminService.revenue_report(
                from_date=from_date, to_date=to_date,
                group_by=group_by, store_id=store_id
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API 62: POST /api/v1/admin/shipments/:orderId/assign | Admin only ─────
    @staticmethod
    def assign_shipper(current_user, order_id):
        try:
            if 'ADMIN' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể gán shipper'}), 403

            data = request.get_json() or {}
            shipper_user_id = data.get('shipper_user_id')

            if not shipper_user_id:
                return jsonify({'success': False, 'message': 'shipper_user_id là bắt buộc'}), 400

            try:
                shipper_user_id = int(shipper_user_id)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'shipper_user_id phải là số nguyên'}), 400

            result, status_code = AdminService.assign_shipper(
                order_id=order_id,
                shipper_user_id=shipper_user_id
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API A: POST /api/v1/admin/roles | Admin only ──────────────────────────
    @staticmethod
    def create_role(current_user):
        try:
            if 'ADMIN' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể tạo role'}), 403

            data = request.get_json() or {}
            role_code = data.get('role_code', '').strip().upper()
            role_name = data.get('role_name', '').strip()
            description = data.get('description', '').strip()

            result, status_code = AdminService.create_role(
                role_code=role_code,
                role_name=role_name,
                description=description
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API B: PATCH /api/v1/admin/roles/:id | Admin only ────────────────────
    @staticmethod
    def update_role(current_user, role_id):
        try:
            if 'ADMIN' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể sửa role'}), 403

            data = request.get_json()
            result, status_code = AdminService.update_role(role_id=role_id, data=data)
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API C: DELETE /api/v1/admin/roles/:id | Admin only ───────────────────
    @staticmethod
    def delete_role(current_user, role_id):
        try:
            if 'ADMIN' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể xóa role'}), 403

            result, status_code = AdminService.delete_role(role_id=role_id)
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # ── API D: DELETE /api/v1/admin/users/:id/roles/:role_id | Admin only ─────
    @staticmethod
    def revoke_role(current_user, user_id, role_id):
        try:
            if 'ADMIN' not in current_user.get('roles', []):
                return jsonify({'success': False, 'message': 'Chỉ Admin mới có thể thu hồi role'}), 403

            result, status_code = AdminService.revoke_role(
                admin_user_id=current_user['user_id'],
                target_user_id=user_id,
                role_id=role_id
            )
            return jsonify(result), status_code

        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
