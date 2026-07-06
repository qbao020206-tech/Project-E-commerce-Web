# migration_add_variants.py
from db_seed_helpers import get_conn

def migrate_products_to_default_variant(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT p.product_id, p.store_id, p.sku, p.price, p.stock_quantity, p.status
        FROM products p
        WHERE p.product_id NOT IN (SELECT product_id FROM product_variants)
    """)
    rows = cur.fetchall()
    print(f"Tìm thấy {len(rows)} sản phẩm cần migrate...")
    for p in rows:
        sku_code = p.sku or f"SKU-PROD-{p.product_id}"
        cur.execute("""
            INSERT INTO product_variants
                (product_id, store_id, sku_code, variant_name, price, stock_quantity, status, is_default)
            VALUES (?, ?, ?, N'Mặc định', ?, ?, ?, 1)
        """, p.product_id, p.store_id, sku_code, p.price, p.stock_quantity, p.status)
    conn.commit()
    print("✓ Migrate xong.")

if __name__ == "__main__":
    conn = get_conn()
    migrate_products_to_default_variant(conn)
    conn.close()