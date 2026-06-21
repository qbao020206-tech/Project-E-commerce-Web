from extensions import db
# Import đối tượng db từ file extensions.py để quản lý kết nối cơ sở dữ liệu
from datetime import datetime 

user_roles = db.Table('user_roles',
    db.Column('user_role_id', db.BigInteger, primary_key=True, autoincrement=True),
    db.Column('user_id', db.BigInteger, db.ForeignKey('users.user_id'), nullable=False),
    db.Column('role_id', db.BigInteger, db.ForeignKey('roles.role_id'), nullable=False),
    db.Column('assigned_by_user_id', db.BigInteger, db.ForeignKey('users.user_id'), nullable=True),
    db.Column('status', db.String(20), nullable=False, default='ACTIVE'),
    db.Column('assigned_at', db.DateTime, default=datetime.utcnow),
    db.Column('revoked_at', db.DateTime, nullable=True, ),
    db.Column('created_at', db.DateTime, default=datetime.utcnow),
    db.Column('updated_at', db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)

class User(db.Model):
    __tablename__='users' 
    # Đặt tên bảng trong cơ sở dữ liệu là 'users' nên sử dụng __tablename__ để chỉ định tên bảng
    
    user_id = db.Column(db.BigInteger,primary_key=True, autoincrement=True)
    email = db.Column(db.String(250), nullable=True, unique=True)   # nullable: user có thể đăng ký chỉ bằng phone
    phone = db.Column(db.String(20), nullable=True, unique=True)     # nullable: user có thể đăng ký chỉ bằng email
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.Unicode(150), nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ACTIVE')
    google_id = db.Column(db.String(225), nullable=True, unique=True)
    facebook_id = db.Column(db.String(225), nullable=True, unique=True)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

  # ĐÂY LÀ PHIÊN BẢN ĐÃ ĐƯỢC CHỈ ĐƯỜNG CỤ THỂ CHO SQLALCHEMY
    roles = db.relationship('Role', secondary=user_roles, lazy='subquery',
        primaryjoin="User.user_id == user_roles.c.user_id",
        secondaryjoin="Role.role_id == user_roles.c.role_id",
        backref=db.backref('users', lazy=True))

    def __repr__(self):
        return f"<User {self.email}>"