from models.category import Category

class CategoryService:
    
    @staticmethod
    def get_all_categories():
        # 1. Lấy danh mục (Chỉ lấy những cái đang ACTIVE và CHƯA BỊ XÓA)
        # Sắp xếp theo display_order (từ nhỏ đến lớn)
        categories = Category.query.filter_by(deleted_at=None, status='ACTIVE').order_by(Category.display_order.asc()).all()
        
        # 2. Đóng gói dữ liệu
        category_list = []
        for cat in categories:
            category_list.append({
                "category_id": cat.category_id,
                "parent_category_id": cat.parent_category_id,
                "category_name": cat.category_name,
                "slug": cat.slug,
                "description": cat.description,
                "icon_url": cat.icon_url,
                "display_order": cat.display_order,
                "status": cat.status
            })
            
        return {
            "status": "success", 
            "message": "Lấy danh sách danh mục thành công!", 
            "data": category_list
        }, 200

    @staticmethod
    def get_category_detail(category_id):
        # 1. Tìm danh mục theo ID (Phải chưa bị xóa)
        category = Category.query.filter_by(category_id=category_id, deleted_at=None).first()
        
        if not category:
            return {"status": "error", "message": "Không tìm thấy danh mục này!"}, 404
            
        # 2. Trả về chi tiết
        return {
            "status": "success",
            "message": "Lấy thông tin chi tiết danh mục thành công!",
            "data": {
                "category_id": category.category_id,
                "parent_category_id": category.parent_category_id,
                "category_name": category.category_name,
                "slug": category.slug,
                "description": category.description,
                "icon_url": category.icon_url,
                "display_order": category.display_order,
                "status": category.status
            }
        }, 200