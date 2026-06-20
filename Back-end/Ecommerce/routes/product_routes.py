from flask import Blueprint
from controllers.product_controller import ProductController

product_bp = Blueprint('products', __name__, url_prefix='/api/v1/products')

product_bp.add_url_rule('', view_func=ProductController.get_products_list, methods=['GET'])
product_bp.add_url_rule('/<int:product_id>', view_func=ProductController.get_product_detail, methods=['GET'])
product_bp.add_url_rule('/<int:product_id>/reviews', view_func=ProductController.get_product_reviews, methods=['GET'])
