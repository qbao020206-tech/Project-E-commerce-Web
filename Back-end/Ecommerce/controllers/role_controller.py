from flask import jsonify
from services.role_service import RoleService

class RoleController:

    @staticmethod
    def get_all_roles():
        result, status_code = RoleService.get_all_roles()
        return jsonify(result), status_code