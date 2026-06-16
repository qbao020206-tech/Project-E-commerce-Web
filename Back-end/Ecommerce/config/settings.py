# File config/settings.py này chứa cấu hình cho ứng dụng Flask, đặc biệt là cấu hình kết nối cơ sở dữ liệu SQL Server.
# Import các thư viện cần thiết
import os 
# Operating System (OS) module để làm việc với các biến môi trường
from dotenv import load_dotenv
# Tải các biến môi trường từ file .env

load_dotenv()
# Lấy URL kết nối cơ sở dữ liệu từ biến môi trường
url_kiem_tra = os.getenv("DATABASE_URL")
print("👉 KIỂM TRA MÔI TRƯỜNG: DATABASE_URL đang là:", url_kiem_tra)

class Config:
    # Flask-SQLAlchemy expects the key `SQLALCHEMY_DATABASE_URI` (not "_URL").
    SQLALCHEMY_DATABASE_URI = url_kiem_tra or os.getenv("DATABASE_URL")
    # Với module dotenv thì đã truy cập vào file .env
    # rồi sau đó lấy module os với method getenv để lấy giá trị của biến môi trường DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Tắt tính năng theo dõi các thay đổi của SQLAlchemy để tiết kiệm tài nguyên
    JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY')
    
    