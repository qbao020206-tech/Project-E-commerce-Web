from flask import Blueprint
from controllers.category_controller import CategoryController

category_bp = Blueprint('categories', __name__, url_prefix='/api/v1')

# API 16: GET /api/v1/categories — Public (không cần token)
category_bp.add_url_rule(
    '/categories',
    view_func=CategoryController.get_all_categories,
    methods=['GET']
)

# API 17: GET /api/v1/categories/:id — Public (không cần token)
category_bp.add_url_rule(
    '/categories/<int:category_id>',
    view_func=CategoryController.get_category_detail,
    methods=['GET']
)