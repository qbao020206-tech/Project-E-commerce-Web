from flask import jsonify
from services.role_service import RoleService


class RoleController:

    # API 15: GET /api/v1/roles | Public — không cần auth
    @staticmethod
    def get_all_roles():
        result, status_code = RoleService.get_all_roles()
        return jsonify(result), status_code