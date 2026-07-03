#!/usr/bin/env python3
"""
seed_categories.py
─────────────────────────────────────────────────────────────────
Seed sẵn 1 cây category mẫu (10 ngành hàng cha, mỗi ngành 3-4 category con)
để products.category_id LUÔN có FK hợp lệ khi crawl — SQLServer_Nhom2.sql
chỉ seed sẵn `roles`, chưa seed category nào.

An toàn chạy lại nhiều lần (idempotent): category đã tồn tại (theo slug)
sẽ KHÔNG bị tạo trùng — chỉ in lại category_id hiện có.

Chạy (sau khi đã chạy SQLServer_Nhom2.sql):
    python seed_categories.py
"""

from db_seed_helpers import get_conn, get_or_create_category

# (Tên category cha, [danh sách category con])
# Lưu ý: tên category con PHẢI khác nhau giữa các nhóm cha — vì idempotency
# check theo slug toàn bảng (xem stable_slug() trong db_seed_helpers.py).
CATEGORY_TREE = [
    ("Điện thoại - Máy tính bảng", ["Điện thoại smartphone", "Máy tính bảng", "Phụ kiện điện thoại"]),
    ("Thời trang", ["Thời trang nam", "Thời trang nữ", "Giày dép", "Túi ví"]),
    ("Điện tử - Điện lạnh", ["Tivi", "Tủ lạnh", "Máy giặt", "Máy lạnh"]),
    ("Máy tính - Laptop", ["Laptop", "Linh kiện máy tính", "Thiết bị mạng", "Phần mềm bản quyền"]),
    ("Đồ gia dụng", ["Đồ dùng nhà bếp", "Đồ dùng phòng tắm", "Nội thất nhỏ"]),
    ("Mẹ và Bé", ["Sữa bột", "Đồ chơi trẻ em", "Quần áo trẻ em", "Tã - Bỉm"]),
    ("Sách - Văn phòng phẩm", ["Sách", "Dụng cụ học tập", "Văn phòng phẩm"]),
    ("Thể thao - Du lịch", ["Dụng cụ thể thao", "Balo - Vali du lịch", "Xe đạp"]),
    ("Làm đẹp - Sức khỏe", ["Mỹ phẩm", "Chăm sóc da", "Thực phẩm chức năng"]),
    ("Ô tô - Xe máy", ["Phụ tùng xe máy", "Phụ kiện ô tô", "Đồ chơi xe điều khiển"]),
]


def main():
    conn = get_conn()
    try:
        total = 0
        for parent_name, children in CATEGORY_TREE:
            parent_id = get_or_create_category(conn, parent_name, parent_category_id=None)
            print(f"✓ {parent_name}  (category_id={parent_id})")
            total += 1
            for child_name in children:
                child_id = get_or_create_category(conn, child_name, parent_category_id=parent_id)
                print(f"   └─ {child_name}  (category_id={child_id})")
                total += 1
        print(f"\nHoàn tất. Tổng {total} category (đã có sẵn thì giữ nguyên, không tạo trùng).")
        print("Dùng đúng các tên category CON ở trên cho cột 'category_name' trong urls.xlsx.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
