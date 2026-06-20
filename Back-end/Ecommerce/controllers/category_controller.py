from flask import jsonify
from services.category_service import CategoryService


class CategoryController:

    # API 16: GET /api/v1/categories | Public
    @staticmethod
    def get_all_categories():
        try:
            result, status_code = CategoryService.get_all_categories()
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500

    # API 17: GET /api/v1/categories/:id | Public
    @staticmethod
    def get_category_detail(category_id):
        try:
            result, status_code = CategoryService.get_category_detail(category_id)
            return jsonify(result), status_code
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500