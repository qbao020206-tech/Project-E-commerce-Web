from models.role import Role


class RoleService:

    # API 15: GET /api/v1/roles | Public
    @staticmethod
    def get_all_roles():
        # Chỉ trả role có status='ACTIVE', sắp xếp theo role_id ASC
        roles = Role.query.filter(Role.status == 'ACTIVE').order_by(Role.role_id.asc()).all()

        role_list = [
            {
                'role_id': role.role_id,
                'role_code': role.role_code,
                'role_name': role.role_name,
                'description': role.description,
            }
            for role in roles
        ]

        return {
            'success': True,
            'data': {
                'roles': role_list
            }
        }, 200