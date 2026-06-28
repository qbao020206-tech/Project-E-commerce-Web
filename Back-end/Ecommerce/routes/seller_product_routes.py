from flask import Blueprint
from controllers.seller_product_controller import SellerProductController
from middlewares.auth_middleware import token_required

seller_product_bp = Blueprint('seller_products', __name__, url_prefix='/api/v1')

# ⚠ Route generate-sku phải đặt TRƯỚC route /<int:product_id>
seller_product_bp.add_url_rule('/seller/products/generate-sku', view_func=token_required(SellerProductController.generate_sku_api), methods=['GET'])
seller_product_bp.add_url_rule('/products', view_func=token_required(SellerProductController.create_product), methods=['POST'])
seller_product_bp.add_url_rule('/products/<int:product_id>', view_func=token_required(SellerProductController.update_product), methods=['PATCH'])
seller_product_bp.add_url_rule('/products/<int:product_id>', view_func=token_required(SellerProductController.delete_product), methods=['DELETE'])
seller_product_bp.add_url_rule('/seller/products', view_func=token_required(SellerProductController.get_seller_products), methods=['GET'])
