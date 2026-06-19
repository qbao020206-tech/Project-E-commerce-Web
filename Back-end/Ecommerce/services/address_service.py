from extensions import db
from models.address import Address
from datetime import datetime 

class AddressService:
    
    @staticmethod
    def add_address(user_id, data):
        is_default = data.get('is_default', False)
        
        if is_default:
            Address.query.filter_by(user_id=user_id, is_default=True).update({'is_default': False})

        new_address = Address(
            user_id=user_id,
            recipient_name=data.get('recipient_name'),
            recipient_phone=data.get('recipient_phone'),
            address_line=data.get('address_line'),
            ward=data.get('ward'),
            district=data.get('district'),
            province=data.get('province'),
            country=data.get('country', 'Việt Nam'),
            is_default=is_default
        )
        
        db.session.add(new_address)
        db.session.commit()

        return {"status": "success", "message": "Thêm địa chỉ mới thành công!"}, 201
        
    @staticmethod
    def get_my_addresses(user_id):
        addresses = Address.query.filter_by(user_id=user_id)\
                                 .order_by(Address.is_default.desc(), Address.created_at.desc())\
                                 .all()

        if not addresses:
            return {"status": "success", "message": "Bạn chưa có địa chỉ nào.", "data": []}, 200

        address_list = []
        for addr in addresses:
            address_list.append({
                "address_id": addr.address_id,
                "recipient_name": addr.recipient_name,
                "recipient_phone": addr.recipient_phone,
                "address_line": addr.address_line,
                "ward": addr.ward,
                "district": addr.district,
                "province": addr.province,
                "country": addr.country,
                "is_default": addr.is_default
            })

        return {
            "status": "success", 
            "message": "Lấy danh sách địa chỉ thành công!", 
            "data": address_list
        }, 200
    
    @staticmethod
    def update_address(user_id, address_id, data):
        # 1. Tìm địa chỉ trong DB. 
        # BẮT BUỘC: Phải lọc theo cả address_id VÀ user_id để tránh hack chéo
        address = Address.query.filter_by(address_id=address_id, user_id=user_id).first()
        
        if not address:
            return {"status": "error", "message": "Không tìm thấy địa chỉ hoặc bạn không có quyền sửa!"}, 404

        # 2. Xử lý logic thông minh: Nếu khách muốn cài địa chỉ này thành Mặc định
        is_default = data.get('is_default', address.is_default)
        if is_default and not address.is_default:
            # Gỡ nhãn mặc định của tất cả địa chỉ cũ đi
            Address.query.filter_by(user_id=user_id, is_default=True).update({'is_default': False})

        # 3. Cập nhật các trường dữ liệu (Khách gửi lên trường nào thì sửa trường đó, không thì giữ nguyên)
        address.recipient_name = data.get('recipient_name', address.recipient_name)
        address.recipient_phone = data.get('recipient_phone', address.recipient_phone)
        address.address_line = data.get('address_line', address.address_line)
        address.ward = data.get('ward', address.ward)
        address.district = data.get('district', address.district)
        address.province = data.get('province', address.province)
        address.country = data.get('country', address.country)
        address.is_default = is_default

        # 4. Lưu thay đổi
        db.session.commit()

        return {"status": "success", "message": "Cập nhật địa chỉ thành công!"}, 200
    
    @staticmethod
    def delete_address(user_id, address_id):
        # 1. Tìm địa chỉ (chỉ tìm những địa chỉ chưa bị xóa - tức là deleted_at = None)
        address = Address.query.filter_by(address_id=address_id, user_id=user_id, deleted_at=None).first()
        
        if not address:
            return {"status": "error", "message": "Không tìm thấy địa chỉ hoặc địa chỉ đã bị xóa!"}, 404

        # 2. Thực hiện XÓA MỀM (Soft Delete)
        address.deleted_at = datetime.utcnow()
        address.status = 'DELETED'
        
        # Nếu xóa trúng địa chỉ mặc định, ta tắt luôn cờ mặc định
        if address.is_default:
            address.is_default = False

        db.session.commit()

        return {"status": "success", "message": "Xóa địa chỉ thành công!"}, 200
    
    @staticmethod
    def set_default_address(user_id, address_id):
        # 1. Tìm địa chỉ cần đặt làm mặc định (chỉ lấy địa chỉ chưa bị xóa)
        address = Address.query.filter_by(address_id=address_id, user_id=user_id, deleted_at=None).first()
        
        if not address:
            return {"status": "error", "message": "Không tìm thấy địa chỉ!"}, 404

        # Nếu nó đã là mặc định sẵn rồi thì báo thành công luôn, khỏi cần làm gì thêm
        if address.is_default:
            return {"status": "success", "message": "Địa chỉ này đang là mặc định rồi!"}, 200

        # 2. Xóa cờ mặc định của TẤT CẢ các địa chỉ cũ của user này
        Address.query.filter_by(user_id=user_id, is_default=True).update({'is_default': False})

        # 3. Bật cờ mặc định cho địa chỉ được chọn
        address.is_default = True
        
        db.session.commit()

        return {"status": "success", "message": "Đã thiết lập địa chỉ mặc định thành công!"}, 200