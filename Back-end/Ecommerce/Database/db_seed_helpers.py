"""
db_seed_helpers.py
─────────────────────────────────────────────────────────────────
Hàm dùng chung cho seed_categories.py và lazada_crawler.py:
  • Kết nối SQL Server (đọc từ .env, Windows Authentication — khớp với app Flask)
  • Faker (vi_VN) + các hàm fallback khi crawl thiếu field
  • Get-or-create cho Category / Seller User / Store / Product (idempotent —
    chạy lại nhiều lần KHÔNG tạo trùng, KHÔNG vi phạm UNIQUE constraint)

Đặt file này CÙNG THƯ MỤC với .env thật của project (Back-end/Ecommerce/Database/
hoặc nơi bạn đang chạy crawler).

Cài thêm thư viện còn thiếu so với requirement.txt hiện tại:
    pip install faker pandas openpyxl
"""

import re
import time
from pathlib import Path
from datetime import datetime

import pyodbc
from dotenv import dotenv_values
from slugify import slugify
from nanoid import generate as nanoid_generate
from faker import Faker
from werkzeug.security import generate_password_hash

# ─── Kết nối DB — đọc đúng .env thật của project (Windows Authentication) ───
BASE_DIR = Path(__file__).resolve().parent
env = dotenv_values(BASE_DIR / ".env")

if "DATABASE_URL" not in env:
    raise RuntimeError(
        f"Không tìm thấy DATABASE_URL trong {BASE_DIR / '.env'}.\n"
        "Đặt db_seed_helpers.py CÙNG thư mục với file .env thật của project."
    )


def _parse_db_url(url: str):
    """Tách SERVER và DATABASE từ DATABASE_URL kiểu SQLAlchemy (mssql+pyodbc://...)."""
    m = re.match(r"mssql\+pyodbc://[^@]*@([^/]+)/([^?]+)", url)
    if not m:
        raise ValueError(f"Không parse được DATABASE_URL: {url}")
    return m.group(1), m.group(2)


_SERVER, _DATABASE = _parse_db_url(env["DATABASE_URL"])


def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={_SERVER};DATABASE={_DATABASE};Trusted_Connection=yes",
        autocommit=False,
    )


# ─── Faker — CHỈ dùng làm fallback khi KHÔNG crawl được field thật ──────────
fake = Faker("vi_VN")

DEFAULT_SELLER_PASSWORD = "Seller@123456"  # mật khẩu demo cho mọi seller tự sinh ra


def stable_slug(text: str, max_len: int = 191) -> str:
    """Slug ổn định, KHÔNG random — dùng cho Category, nơi cần so khớp đúng
    slug để biết category đã tồn tại chưa (idempotent theo tên)."""
    return slugify(text or "item")[:max_len] or "item"


def unique_slug(text: str, max_len: int = 191) -> str:
    """Slug có suffix random — dùng cho Store/Product vì 2 tin đăng khác nhau
    có thể trùng tên, mà slug lại phải UNIQUE toàn bảng."""
    base = slugify(text or "item")[: max_len - 7] or "item"
    return f"{base}-{nanoid_generate(size=6).lower()}"


def safe_store_code(text: str, max_len: int = 30) -> str:
    return slugify(text or f"shop-{nanoid_generate(size=6)}")[:max_len]


# ─── Fallback generators — CHỈ áp dụng khi scraping không lấy được giá trị thật ─
def fallback_price() -> float:
    """Lazada không phải lúc nào cũng lộ giá ở chỗ script tìm (sale ẩn, lazy-load,
    A/B layout khác nhau...). Sinh giá demo hợp lý thay vì để 0 — nếu để 0 sẽ vi
    phạm CHECK (price > 0) và sản phẩm đó sẽ bị DB từ chối hoàn toàn."""
    return float(fake.random_int(min=29_000, max=2_000_000, step=1_000))


def fallback_stock() -> int:
    """Lazada KHÔNG công khai số tồn kho thật trên trang listing/detail — trường
    này luôn là số mô phỏng, không phải vì 'crawl lỗi'. Để > 0 thì sản phẩm mới
    đặt hàng thử được qua API place_order."""
    return fake.random_int(min=5, max=300)


def fallback_description(product_name: str, category_name: str = "") -> str:
    """Dùng template tiếng Việt thay vì fake.text(): Faker vi_VN không có
    provider lorem-ipsum tiếng Việt thật, fake.text()/fake.paragraph() sẽ vẫn
    ra Lorem Ipsum tiếng Latin trông rất lạc quẻ khi chen vào giữa data tiếng Việt."""
    cat_part = f" thuộc danh mục {category_name}" if category_name else ""
    return (
        f"{product_name}{cat_part}. Sản phẩm chính hãng, đầy đủ phụ kiện theo "
        f"tiêu chuẩn nhà sản xuất, hỗ trợ đổi trả trong 7 ngày nếu phát hiện lỗi "
        f"từ nhà sản xuất."
    )


def placeholder_image_url(seed_text: str) -> str:
    """Dùng khi KHÔNG crawl được ảnh thật nào cho sản phẩm. Đây là ảnh
    placeholder public, KHÔNG phải ảnh sản phẩm thật — chỉ để storefront không
    vỡ layout vì thiếu ảnh hoàn toàn."""
    safe = re.sub(r"[^a-zA-Z0-9]", "", seed_text)[:20] or "product"
    return f"https://placehold.co/600x600?text={safe}"


# ─── Get-or-create: Category ─────────────────────────────────────────────────
def get_or_create_category(conn, category_name: str, parent_category_id=None) -> int:
    """Trả category_id nếu đã tồn tại (theo slug), nếu chưa thì tạo mới.
    Idempotent — gọi lại nhiều lần với cùng tên KHÔNG tạo trùng."""
    cur = conn.cursor()
    slug = stable_slug(category_name)

    cur.execute("SELECT category_id FROM categories WHERE slug = ?", slug)
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        """
        INSERT INTO categories
            (parent_category_id, category_name, slug, status, display_order, created_at, updated_at)
        OUTPUT INSERTED.category_id
        VALUES (?, ?, ?, 'ACTIVE', 0, GETDATE(), GETDATE())
        """,
        parent_category_id, category_name, slug,
    )
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def find_category_id_by_name(conn, category_name: str):
    """Tra category_id theo tên (không phân biệt hoa/thường) — crawler dùng
    hàm này để map cột category_name trong urls.xlsx ra category_id thật."""
    cur = conn.cursor()
    cur.execute(
        "SELECT category_id FROM categories WHERE LOWER(category_name) = LOWER(?)",
        category_name,
    )
    row = cur.fetchone()
    return row[0] if row else None


# ─── Get-or-create: Seller user + Store + user_stores (OWNER) ───────────────
def get_or_create_store_with_owner(conn, store_data: dict) -> int:
    """
    Idempotent:
      1. Nếu store_code đã tồn tại → trả về store_id cũ, KHÔNG insert lại
         (vd. crawl lại đúng shop đó ở lần chạy sau).
      2. Nếu store mới → tạo Store, tạo 1 User 'seller' RIÊNG cho store này
         (lưu ý: UX_one_active_owner_per_user trong DB chỉ cho phép 1 user
         làm OWNER của ĐÚNG 1 store, nên không thể dùng chung 1 seller cho
         nhiều store), gán role SELLER vào user_roles, gán OWNER vào user_stores.
      3 thao tác 2-4 nằm trong 1 transaction — lỗi ở bước nào cũng rollback hết,
        không để lại store "mồ côi" nửa chừng.

    Trả về store_id.
    """
    cur = conn.cursor()

    cur.execute("SELECT store_id FROM stores WHERE store_code = ?", store_data["store_code"])
    row = cur.fetchone()
    if row:
        return row[0]

    try:
        # 1) Insert store — status LUÔN viết hoa 'ACTIVE'
        #    (đây chính là bug khiến 2 script gốc insert fail 100%: chúng dùng 'active')
        cur.execute(
            """
            INSERT INTO stores (
                store_code, store_name, slug, description, logo_url,
                contact_phone, address_line, ward, district, province,
                total_products, status, created_at, updated_at
            )
            OUTPUT INSERTED.store_id
            VALUES (?,?,?,?,?,?,?,?,?,?,?,'ACTIVE',GETDATE(),GETDATE())
            """,
            store_data["store_code"], store_data["store_name"], store_data["slug"],
            store_data["description"], store_data["logo_url"], store_data["contact_phone"],
            store_data["address_line"], store_data["ward"], store_data["district"],
            store_data["province"], store_data["total_products"],
        )
        store_id = cur.fetchone()[0]

        # 2) Tạo user 'seller' riêng cho store này — email/phone sinh DETERMINISTIC
        #    theo store_code/store_id để KHÔNG BAO GIỜ đụng UNIQUE(email)/UNIQUE(phone)
        seller_email = f"seller.{store_data['store_code']}@example.com"
        seller_phone = f"0900{store_id:06d}"
        seller_name = fake.name()
        password_hash = generate_password_hash(DEFAULT_SELLER_PASSWORD)

        cur.execute(
            """
            INSERT INTO users (email, phone, password_hash, full_name, status, created_at, updated_at)
            OUTPUT INSERTED.user_id
            VALUES (?,?,?,?,'ACTIVE',GETDATE(),GETDATE())
            """,
            seller_email, seller_phone, password_hash, seller_name,
        )
        seller_user_id = cur.fetchone()[0]

        # 3) Gán role SELLER (role này phải đã được seed sẵn bởi SQLServer_Nhom2.sql)
        cur.execute("SELECT role_id FROM roles WHERE role_code = 'SELLER'")
        role_row = cur.fetchone()
        if not role_row:
            raise RuntimeError(
                "Không tìm thấy role SELLER trong bảng roles — chạy lại SQLServer_Nhom2.sql trước."
            )
        seller_role_id = role_row[0]

        cur.execute(
            """
            INSERT INTO user_roles (user_id, role_id, status, assigned_at, created_at, updated_at)
            VALUES (?, ?, 'ACTIVE', GETDATE(), GETDATE(), GETDATE())
            """,
            seller_user_id, seller_role_id,
        )

        # 4) Gán OWNER trong user_stores
        cur.execute(
            """
            INSERT INTO user_stores (user_id, store_id, store_member_role, is_active, created_at, updated_at)
            VALUES (?, ?, 'OWNER', 1, GETDATE(), GETDATE())
            """,
            seller_user_id, store_id,
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    print(f"    ✓ Seller mới: {seller_email}  |  mật khẩu: {DEFAULT_SELLER_PASSWORD}  (user_id={seller_user_id})")
    return store_id


# ─── Product: tra cứu idempotent theo (store_id, sku) ───────────────────────
def find_existing_product_id(conn, store_id: int, sku: str):
    cur = conn.cursor()
    cur.execute(
        "SELECT product_id FROM products WHERE store_id = ? AND sku = ?",
        store_id, sku,
    )
    row = cur.fetchone()
    return row[0] if row else None


def insert_product_with_images(conn, store_id: int, category_id: int, product: dict, images: list):
    """Insert product + product_images trong 1 transaction (status LUÔN 'ACTIVE').
    Gọi find_existing_product_id() trước hàm này ở phía caller để quyết định
    insert mới hay bỏ qua — tách riêng để caller có thể log rõ ràng new/skip."""
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO products (
                store_id, category_id, sku, product_name, slug, description,
                price, stock_quantity, sold_quantity, status, created_at, updated_at
            )
            OUTPUT INSERTED.product_id
            VALUES (?,?,?,?,?,?,?,?,?,'ACTIVE',GETDATE(),GETDATE())
            """,
            store_id, category_id, product["sku"], product["product_name"],
            product["slug"], product["description"], product["price"],
            product["stock_quantity"], product["sold_quantity"],
        )
        pid = cur.fetchone()[0]

        for img in images:
            cur.execute(
                """
                INSERT INTO product_images
                    (product_id, image_url, alt_text, display_order, is_primary, created_at, updated_at)
                VALUES (?,?,?,?,?,GETDATE(),GETDATE())
                """,
                pid, img["image_url"], img["alt_text"], img["display_order"], img["is_primary"],
            )

        conn.commit()
        return pid
    except Exception:
        conn.rollback()
        raise
