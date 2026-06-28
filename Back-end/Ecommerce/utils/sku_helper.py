import unicodedata
import re


def remove_viet(text: str) -> str:
    """Chuyển tiếng Việt có dấu sang không dấu."""
    # Xử lý đặc biệt cho chữ đ/Đ trước (không convert được qua NFD)
    text = re.sub(r'[đĐ]', lambda m: 'd' if m.group().islower() else 'D', text)
    normalized = unicodedata.normalize('NFD', text)
    return normalized.encode('ascii', 'ignore').decode('ascii')


def build_prefix(name: str) -> str:
    """Tạo prefix SKU từ tên sản phẩm."""
    no_accent = remove_viet(name)
    # Chỉ giữ chữ cái và số, bỏ ký tự đặc biệt
    clean = re.sub(r'[^A-Za-z0-9\s]', '', no_accent).strip()
    words = clean.upper().split()
    words = [w for w in words if w]  # bỏ từ rỗng
    if not words:
        return 'SKU'
    if len(words) == 1:
        return words[0][:4]  # 1 từ → lấy 4 ký tự đầu
    return ''.join(w[0] for w in words[:4])  # nhiều từ → chữ đầu mỗi từ, tối đa 4


def generate_sku(name: str, store_id: int, db_session) -> str:
    """
    Sinh SKU duy nhất cho sản phẩm trong store.
    Trả về chuỗi SKU chưa tồn tại trong DB.
    Sử dụng SQLAlchemy session thay vì raw connection.
    """
    from models.product import Product

    prefix = build_prefix(name) or 'SKU'

    for counter in range(1, 1000):
        candidate = f"{prefix}-{counter:03d}"  # ATBT-001, ATBT-002, ...
        existing = db_session.query(Product).filter(
            Product.store_id == store_id,
            Product.sku == candidate
        ).first()
        if not existing:
            return candidate

    # Fallback nếu cạn 999 số (rất hiếm)
    import time
    return f"{prefix}-{int(time.time()) % 100000}"
