#!/usr/bin/env python3
"""
Lazada Vietnam Shop Crawler → SQL Server
=========================================
Cài đặt:
    pip install playwright pyodbc
    playwright install chromium

Chạy:
    python lazada_crawler.py <shop_url> [category_id]

Ví dụ:
    python lazada_crawler.py https://www.lazada.vn/shop/ten-shop/ 3
"""

import asyncio
import sys
import re
import time
import random
import pyodbc
from playwright.async_api import async_playwright

# ══════════════════════════════════════════════
# ⚙️  CẤU HÌNH – SỬA THÔNG TIN KẾT NỐI Ở ĐÂY
# ══════════════════════════════════════════════
DB_SERVER   = "Admin-PC"        # hoặc DESKTOP-ABC\SQLEXPRESS
DB_NAME     = "TechTonicEcommerce_"
DB_USER     = "sa"
DB_PASSWORD = "YourPassword"
# ══════════════════════════════════════════════


def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_SERVER};DATABASE={DB_NAME};"
        f"UID={DB_USER};PWD={DB_PASSWORD}",
        autocommit=False
    )


def rand_sleep(a=1.5, b=4.0):
    time.sleep(random.uniform(a, b))

def to_int(s) -> int:
    m = re.search(r"\d+", str(s).replace(",", "").replace(".", ""))
    return int(m.group()) if m else 0

def to_float(s) -> float:
    m = re.search(r"\d+", str(s).replace(",", "").replace(".", ""))
    return float(m.group()) if m else 0.0

async def el_text(page, *selectors, default="") -> str:
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el:
                t = (await el.inner_text()).strip()
                if t:
                    return t
        except Exception:
            pass
    return default

async def el_attr(page, selector, attr, default="") -> str:
    try:
        el = await page.query_selector(selector)
        if el:
            val = await el.get_attribute(attr)
            return (val or default).strip()
    except Exception:
        pass
    return default


async def check_blocked(page) -> bool:
    """Phát hiện CAPTCHA, chờ user giải thủ công."""
    content = (await page.content()).lower()
    blocked = any(k in content for k in ["captcha", "robot", "verify", "access denied"])
    if blocked:
        print("\n⚠️  CAPTCHA DETECTED!")
        print("   → Giải CAPTCHA trong cửa sổ trình duyệt mở.")
        print("   → Sau khi xong nhấn ENTER để tiếp tục...")
        input()
        return True
    return False


async def crawl_shop(page, shop_url: str) -> dict:
    await page.goto(shop_url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)
    await check_blocked(page)

    name = await el_text(page,
        "[class*='shop-name']", "[class*='seller-name']", "h1",
        default="Unknown Shop"
    )
    logo = await el_attr(page, "[class*='shop-logo'] img", "src") \
        or await el_attr(page, "[class*='seller-logo'] img", "src")
    desc = await el_text(page,
        "[class*='shop-desc']", "[class*='seller-desc']",
        "[class*='shop-introduction']", default=""
    )

    contact_phone = address_line = ward = district = province = ""
    try:
        raw = await page.evaluate("JSON.stringify(window.__init_data__ || {})")
        for key, var in [("phone", "contact_phone"), ("address", "address_line"),
                         ("province", "province"), ("district", "district"), ("ward", "ward")]:
            m = re.search(rf'"{key}"\s*:\s*"([^"]+)"', raw)
            if m:
                locals()[var]  # just to reference; assign below
        phones    = re.findall(r'"phone"\s*:\s*"([^"]+)"', raw)
        addrs     = re.findall(r'"address"\s*:\s*"([^"]+)"', raw)
        provs     = re.findall(r'"province"\s*:\s*"([^"]+)"', raw)
        dists     = re.findall(r'"district"\s*:\s*"([^"]+)"', raw)
        wards     = re.findall(r'"ward"\s*:\s*"([^"]+)"', raw)
        contact_phone = phones[0][:20]  if phones else ""
        address_line  = addrs[0][:255]  if addrs  else ""
        province      = provs[0][:100]  if provs  else ""
        district      = dists[0][:100]  if dists  else ""
        ward          = wards[0][:100]  if wards  else ""
    except Exception:
        pass

    total_text = await el_text(page,
        "[class*='product-count']", "[class*='total-product']", default="0"
    )
    total = to_int(total_text)

    m = re.search(r"lazada\.vn/shop/([^/?]+)", shop_url)
    slug = m.group(1) if m else re.sub(r"[^\w-]", "-", name.lower())[:191]
    store_code = slug[:30]

    return {
        "store_code":     store_code,
        "store_name":     name[:150],
        "slug":           slug[:191],
        "description":    desc[:4000] if desc else None,
        "logo_url":       logo[:500]  if logo else None,
        "contact_phone":  contact_phone or None,
        "address_line":   address_line  or None,
        "ward":           ward          or None,
        "district":       district      or None,
        "province":       province      or None,
        "total_products": total,
        "status":         "active",
    }


def db_insert_store(data: dict) -> int:
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO stores (
            store_code, store_name, slug, description, logo_url,
            contact_phone, address_line, ward, district, province,
            total_products, status, created_at, updated_at
        )
        OUTPUT INSERTED.store_id
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,GETDATE(),GETDATE())
    """,
    data["store_code"], data["store_name"], data["slug"],
    data["description"], data["logo_url"], data["contact_phone"],
    data["address_line"], data["ward"], data["district"], data["province"],
    data["total_products"], data["status"])
    sid = cur.fetchone()[0]
    con.commit()
    con.close()
    return sid


async def get_product_links(page) -> list:
    hrefs = set()

    # Ưu tiên đọc từ JS (nhanh hơn, đầy đủ hơn)
    for js_var in ["window.__LZD_P_DATA__", "window.__init_data__"]:
        try:
            raw = await page.evaluate(f"JSON.stringify({js_var} || null)")
            if raw:
                found = re.findall(
                    r'"(https?://www\.lazada\.vn/products?/[^"]+\.html)"', raw
                )
                hrefs.update(found)
        except Exception:
            pass

    # DOM fallback
    if not hrefs:
        cards = await page.query_selector_all(
            "a[href*='/products/'], a[href*='lazada.vn/products']"
        )
        for c in cards:
            h = await c.get_attribute("href") or ""
            if ".html" in h:
                if h.startswith("//"):
                    h = "https:" + h
                hrefs.add(h.split("?")[0])

    return list(hrefs)


async def crawl_product(page, url: str, store_id: int, category_id: int):
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(2)
    await check_blocked(page)

    name = price = sku = desc = ""
    sold   = 0
    images = []

    try:
        raw = await page.evaluate("JSON.stringify(window.__init_data__ || {})")

        m = re.search(r'"subject"\s*:\s*"([^"]+)"', raw)
        if m: name = m.group(1)

        prices = re.findall(r'"price"\s*:\s*"([\d,]+)"', raw)
        if prices: price = float(prices[0].replace(",", ""))

        m_sold = re.search(r'"salesCountShow"\s*:\s*"([^"]+)"', raw)
        if m_sold: sold = to_int(m_sold.group(1))

        m_sku = re.search(r'"skuId"\s*:\s*"(\d+)"', raw)
        if m_sku: sku = m_sku.group(1)[:50]

        m_desc = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        if m_desc:
            try: desc = m_desc.group(1).encode().decode("unicode_escape")
            except Exception: desc = m_desc.group(1)

        img_urls = re.findall(
            r'(https://img\.lazcdn\.com[^\\"<>]+\.(?:jpg|png|webp))', raw
        )
        seen = set()
        for u in img_urls:
            u_clean = re.sub(r'_\d+x\d+[^.]*', '', u)
            if u_clean not in seen:
                seen.add(u_clean)
                images.append(u_clean)
    except Exception:
        pass

    # DOM fallback
    if not name:
        name = await el_text(page,
            "[class*='pdp-product-title']", "[class*='title--wrap']", "h1",
            default="Unknown Product"
        )
    if not price:
        pt = await el_text(page, "[class*='pdp-price']", default="0")
        price = to_float(pt.split("–")[0])
    if not sold:
        st = await el_text(page, "[class*='sold']", default="0")
        sold = to_int(st)
    if not images:
        img_els = await page.query_selector_all(
            "[class*='gallery'] img, [class*='item-gallery'] img"
        )
        for el in img_els:
            src = await el.get_attribute("src") or await el.get_attribute("data-src") or ""
            if "lazcdn" in src and src not in images:
                images.append(src)

    if not sku:
        m_url = re.search(r"-s(\d+)\.html", url)
        sku = m_url.group(1)[:50] if m_url else str(int(time.time()))[-10:]

    m_slug = re.search(r"lazada\.vn/products?/(.+?)(?:\?|$)", url)
    slug_raw = m_slug.group(1) if m_slug else name
    slug = re.sub(r"-i\d+-s\d+", "", slug_raw)[:191]

    product = {
        "store_id":       store_id,
        "category_id":    category_id,
        "sku":            sku,
        "product_name":   name[:200],
        "slug":           slug,
        "description":    desc[:8000] if desc else None,
        "price":          float(price),
        "stock_quantity": 0,
        "sold_quantity":  int(sold),
        "status":         "active",
    }

    img_records = [
        {
            "image_url":     u[:500],
            "alt_text":      name[:255],
            "display_order": i,
            "is_primary":    1 if i == 0 else 0,
        }
        for i, u in enumerate(images[:20])
    ]

    return product, img_records


def db_insert_product(product: dict, images: list) -> int:
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO products (
            store_id, category_id, sku, product_name, slug, description,
            price, stock_quantity, sold_quantity, status, created_at, updated_at
        )
        OUTPUT INSERTED.product_id
        VALUES (?,?,?,?,?,?,?,?,?,?,GETDATE(),GETDATE())
    """,
    product["store_id"],   product["category_id"],  product["sku"],
    product["product_name"], product["slug"],        product["description"],
    product["price"],      product["stock_quantity"],
    product["sold_quantity"], product["status"])

    pid = cur.fetchone()[0]

    for img in images:
        cur.execute("""
            INSERT INTO product_images
                (product_id, image_url, alt_text, display_order, is_primary, created_at, updated_at)
            VALUES (?,?,?,?,?,GETDATE(),GETDATE())
        """, pid, img["image_url"], img["alt_text"],
             img["display_order"], img["is_primary"])

    con.commit()
    con.close()
    return pid


async def main():
    if len(sys.argv) < 2:
        print("Cách dùng: python lazada_crawler.py <shop_url> [category_id]")
        print("Ví dụ:     python lazada_crawler.py https://www.lazada.vn/shop/abc/ 5")
        sys.exit(1)

    shop_url    = sys.argv[1].rstrip("/") + "/"
    category_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,   # QUAN TRỌNG: False để tránh bị chặn
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
            ]
        )
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="vi-VN",
        )
        page = await ctx.new_page()
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # ── SHOP ────────────────────────────────
        print("\n" + "═"*60)
        print(f"[1] Crawl shop: {shop_url}")
        print("═"*60)
        shop_data = await crawl_shop(page, shop_url)
        print(f"    Tên      : {shop_data['store_name']}")
        print(f"    Tổng sp  : {shop_data['total_products']}")
        print(f"    Tỉnh/TP  : {shop_data['province'] or 'N/A'}")

        store_id = db_insert_store(shop_data)
        print(f"    ✓ Lưu DB → store_id = {store_id}")

        # ── PRODUCTS ────────────────────────────
        print(f"\n[2] Crawl sản phẩm (category_id={category_id})")
        print("═"*60)

        done      = 0
        page_num  = 1
        max_empty = 2
        empty_cnt = 0

        while True:
            listing_url = f"{shop_url}?page={page_num}"
            print(f"\n  📄 Trang {page_num}: {listing_url}")

            await page.goto(listing_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(3)
            await check_blocked(page)

            links = await get_product_links(page)

            if not links:
                empty_cnt += 1
                print(f"     → Không có link ({empty_cnt}/{max_empty})")
                if empty_cnt >= max_empty:
                    print("     → Đã hết sản phẩm.")
                    break
                page_num += 1
                rand_sleep(2, 4)
                continue

            empty_cnt = 0
            print(f"     → {len(links)} sản phẩm")

            for link in links:
                try:
                    print(f"     [{done+1:>4}] {link[:65]}")
                    product, imgs = await crawl_product(page, link, store_id, category_id)
                    pid = db_insert_product(product, imgs)
                    print(f"            ✓ {product['product_name'][:40]}")
                    print(f"              Giá: {product['price']:,.0f}đ | Bán: {product['sold_quantity']} | Ảnh: {len(imgs)} | id={pid}")
                    done += 1
                except Exception as e:
                    print(f"            ✗ Lỗi: {e}")

                rand_sleep(1.5, 3.5)

            page_num += 1
            rand_sleep(2, 5)

        await browser.close()

    print("\n" + "═"*60)
    print(f"✅ XONG! {done} sản phẩm → store_id = {store_id}")
    print("═"*60)


if __name__ == "__main__":
    asyncio.run(main())