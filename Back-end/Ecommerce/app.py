# app.py: Tạo ứng dụng Flask và cấu hình kết nối cơ sở dữ liệu
from flask import Flask 
# Import Flask để tạo ứng dụng web
from config.settings import Config 
# Import lớp Config từ file config/settings.py để lấy cấu hình kết nối cơ sở dữ liệu
from extensions import db
# Import đối tượng db từ file extensions.py để quản lý kết nối cơ sở dữ liệu
from routes.auth_routes import auth_bp
# Import Blueprint auth_bp từ file routes/authu_routes.py để đăng ký các route liên quan đến xác thực người dùng
from routes.user_routes import user_bp
from routes.address_routes import address_bp
from routes.role_routes import role_bp
from routes.product_routes import product_bp
from routes.category_routes import category_bp
from routes.seller_product_routes import seller_product_bp
from routes.store_routes import store_bp
from routes.cart_routes import cart_bp
from routes.order_routes import order_bp
from routes.seller_order_routes import seller_order_bp
from routes.review_routes import review_bp
from routes.conversation_routes import conversation_bp
from routes.voucher_routes import voucher_bp
from routes.shipment_routes import shipment_bp
from routes.admin_routes import admin_bp
from models.refresh_token import RefreshToken  # Đăng ký bảng refresh_tokens với SQLAlchemy

def create_app():
    # Khởi tạo ứng dụng Flask
    app= Flask(__name__)
    # Nạp cấu hình từ file Config từ file config/settings.py vào ứng dụng Flask
    app.config.from_object(Config)
    # Dòng này nhặt toàn bộ cấu hình từ lớp Config và áp dụng vào ứng dụng Flask
    db.init_app(app)
    # db Khởi tạo kết nối cơ sở dữ liệu với ứng dụng Flask bằng cách gọi phương thức init_app của đối tượng db
    app.register_blueprint(auth_bp)
    # Đăng ký Blueprint auth_bp vào ứng dụng Flask để các route trong auth_bp có thể được sử dụng
    app.register_blueprint(user_bp)
    app.register_blueprint(address_bp)
    app.register_blueprint(role_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(seller_product_bp)
    app.register_blueprint(store_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(seller_order_bp)
    app.register_blueprint(review_bp)
    app.register_blueprint(conversation_bp)
    app.register_blueprint(voucher_bp)
    app.register_blueprint(shipment_bp)
    app.register_blueprint(admin_bp)
    with app.app_context():
        try:
            from sqlalchemy import text
            # Import text từ SQLAlchemy để thực thi câu lệnh SQL
            db.session.execute(text("SELECT 1"))
            # Thực thi câu lệnh SQL "SELECT 1" để kiểm tra kết nối cơ sở dữ liệu
            print("Kết nối cơ sở dữ liệu thành công!")
        except Exception as e:
            print("Kết nối cơ sở dữ liệu thất bại:", str(e))
    # Trả về app để có thể dùng khi chạy hoặc cho testing
    return app
            
if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
       

    

    

    

    


