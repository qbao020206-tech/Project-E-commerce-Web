from flask import Blueprint
from controllers.category_controller import CategoryController

category_bp = Blueprint('category', __name__, url_prefix='/api/v1/categories')

# API 1: Lấy danh sách (GET /api/v1/categories)
@category_bp.route('/', methods=['GET'], strict_slashes=False)
def get_all_categories():
    return CategoryController.get_all_categories()

# API 2: Lấy chi tiết 1 danh mục (GET /api/v1/categories/<id>)
@category_bp.route('/<int:category_id>', methods=['GET'], strict_slashes=False)
def get_category_detail(category_id):
    return CategoryController.get_category_detail(category_id)