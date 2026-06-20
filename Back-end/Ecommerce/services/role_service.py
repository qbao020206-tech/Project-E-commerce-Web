from models.role import Role

class RoleService:
    
    @staticmethod
    def get_all_roles():
        # 1. Truy vấn lấy toàn bộ quyền từ DB
        roles = Role.query.all()
        
        # 2. Chuyển đổi dữ liệu sang dạng JSON
        role_list = []
        for role in roles:
            role_list.append({
                "role_id": role.role_id,
                "role_name": role.role_name,
                "description": role.description
            })
            
        return {
            "status": "success", 
            "message": "Lấy danh sách quyền thành công!", 
            "data": role_list
        }, 200