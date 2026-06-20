from flask import jsonify
from services.category_service import CategoryService

class CategoryController:
    
    @staticmethod
    def get_all_categories(): # KHÔNG CÓ current_user vì ai cũng xem được
        result, status_code = CategoryService.get_all_categories()
        return jsonify(result), status_code
        
    @staticmethod
    def get_category_detail(category_id): # KHÔNG CÓ current_user
        result, status_code = CategoryService.get_category_detail(category_id)
        return jsonify(result), status_code