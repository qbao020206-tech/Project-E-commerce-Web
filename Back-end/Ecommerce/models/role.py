from extensions import db
from datetime import datetime

class Role(db.Model):
    __tablename__ = 'roles'
    
    role_id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    role_code = db.Column(db.String(30), nullable=False, unique=True)
    role_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='ACTIVE')
    is_system_role = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        
        return f"<role {self.role_code}>"
# <role {self.role_code}> là một phương thức đặc biệt trong Python được gọi là 
# "magic method" hoặc "dunder method". Nó được sử dụng để định nghĩa cách mà đối tượng của lớp 
# Role sẽ được biểu diễn dưới dạng chuỗi khi bạn in nó ra hoặc khi bạn sử dụng hàm str() trên đối tượng đó. 
# Trong trường hợp này, nó sẽ trả về một chuỗi có định dạng "<role {self.role_code}>", 
# trong đó {self.role_code} sẽ được thay thế bằng giá trị của thuộc tính role_code của đối tượng Role. 
# Ví dụ, nếu bạn có một đối tượng Role với role_code là "ADMIN", thì khi bạn in đối tượng đó, nó sẽ hiển thị "<role ADMIN>". 