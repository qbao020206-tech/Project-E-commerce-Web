#!/usr/bin/env python3
"""
Lazada Vietnam Shop Crawler
─────────────────────────────
Cài đặt:
    pip install playwright pyodbc python-dotenv openpyxl pandas
    playwright install chromium

Cấu trúc thư mục:
    your_folder/
    ├── lazada_crawler.py
    ├── .env                ← file có sẵn
    └── urls.xlsx           ← tạo file này (xem hướng dẫn bên dưới)

urls.xlsx cần 2 cột:
    A: shop_url          B: category_id
    https://lazada.vn/shop/abc/     3
    https://lazada.vn/shop/xyz/     5

Chạy:
    python lazada_crawler.py
"""

import asyncio
import re
import time
import random
import unicodedata
import pyodbc
import pandas as pd
from pathlib import Path
from dotenv import dotenv_values
from playwright.async_api import async_playwright

# ─── Đọc .env ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
env      = dotenv_values(BASE_DIR / ".env")

def _parse_db_url(url: str) -> tuple[str, str]:
    """Tách SERVER và DATABASE từ DATABASE_URL kiểu SQLAlchemy."""
    # mssql+pyodbc://@Server/Database?...
    m = re.match(r"mssql\+pyodbc://[^@]*@([^/]+)/([^?]+)", url)
    if not m:
        raise ValueError(f"Không parse được DATABASE_URL: {url}")
    return m.group(1), m.group(2)

_SERVER, _DATABASE = _parse_db_url(env["DATABASE_URL"])

def get_conn():
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={_SERVER};DATABASE={_DATABASE};Trusted_Connection=yes",
        autocommit=False
    )

# ─── Đọc danh sách URL từ Excel ──────────────────────────────
def load_urls() -> list[dict]:
    xlsx = BASE_DIR / "urls.xlsx"
    if not xlsx.exists():
        raise FileNotFoundError(
            "Không tìm thấy urls.xlsx!\n"
            "Tạo file với 2 cột: shop_url | category_id"
        )
    df = pd.read_excel(xlsx, dtype=str)

    def _normalize_col_name(name: str) -> str:
        clean = str(name).strip()
        clean = unicodedata.normalize('NFKD', clean)
        clean = clean.encode('ascii', 'ignore').decode('ascii')
        clean = clean.lower().replace(' ', '_')
        return re.sub(r'[^a-z0-9_]', '', clean)

    col_map = {_normalize_col_name(c): c for c in df.columns}
    shop_col = None
    for candidate in [
        "shop_url", "shopurl", "url", "url_cua_hang",
        "urlcuhang", "urlcuhng", "url_cua_hang_"
    ]:
        if candidate in col_map:
            shop_col = col_map[candidate]
            break
    if not shop_col:
        print(f"  DEBUG – Cột đọc được: {list(col_map.keys())}")
        raise ValueError("Excel thiếu cột 'shop_url' hoặc cột URL cửa hàng")

    category_col = col_map.get(
        "category_id",
        next((col_map[c] for c in ["categoryid", "category"] if c in col_map), None)
    )

    rows = []
    for _, r in df.iterrows():
        url = str(r.get(shop_col, "")).strip()
        url = url.split("?")[0]   # bỏ ?spm=... ở cuối URL
        if not url or url in ("nan", "") or url.startswith("#"):
            continue
        cat_raw = r.get(category_col, "1") if category_col else "1"
        try:
            cat = int(float(str(cat_raw)))
        except Exception:
            cat = 1
        rows.append({"shop_url": url, "category_id": cat})
    return rows

# ─── Utilities ───────────────────────────────────────────────
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
            return (await el.get_attribute(attr) or default).strip()
    except Exception:
        pass
    return default

async def check_blocked(page) -> bool:
    content = (await page.content()).lower()
    if any(k in content for k in ["captcha", "robot", "verify", "access denied"]):
        print("\n⚠️  CAPTCHA! Giải trong cửa sổ trình duyệt rồi nhấn ENTER...")
        input()
        return True
    return False

# ─── Crawl shop ──────────────────────────────────────────────
async def crawl_shop(page, shop_url: str) -> dict:
    await page.goto(shop_url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(3)
    await check_blocked(page)

    name = await el_text(page,
        "[class*='shop-name']", "[class*='seller-name']", "h1",
        default="Unknown Shop"
    )
    logo = (await el_attr(page, "[class*='shop-logo'] img", "src")
            or await el_attr(page, "[class*='seller-logo'] img", "src"))
    desc = await el_text(page,
        "[class*='shop-desc']", "[class*='seller-desc']",
        "[class*='shop-introduction']", default=""
    )

    contact_phone = address_line = ward = district = province = ""
    try:
        raw = await page.evaluate("JSON.stringify(window.__init_data__ || {})")
        for key, lst_name in [("phone","phones"), ("address","addrs"),
                               ("province","provs"), ("district","dists"), ("ward","wards")]:
            pass  # parse below
        phones = re.findall(r'"phone"\s*:\s*"([^"]+)"', raw)
        addrs  = re.findall(r'"address"\s*:\s*"([^"]+)"', raw)
        provs  = re.findall(r'"province"\s*:\s*"([^"]+)"', raw)
        dists  = re.findall(r'"district"\s*:\s*"([^"]+)"', raw)
        wards  = re.findall(r'"ward"\s*:\s*"([^"]+)"', raw)
        contact_phone = phones[0][:20]  if phones else ""
        address_line  = addrs[0][:255]  if addrs  else ""
        province      = provs[0][:100]  if provs  else ""
        district      = dists[0][:100]  if dists  else ""
        ward          = wards[0][:100]  if wards  else ""
    except Exception:
        pass

    total = to_int(await el_text(page,
        "[class*='product-count']", "[class*='total-product']", default="0"
    ))

    m    = re.search(r"lazada\.vn/shop/([^/?]+)", shop_url)
    slug = m.group(1) if m else re.sub(r"[^\w-]", "-", name.lower())[:191]

    return {
        "store_code":     slug[:30],
        "store_name":     name[:150],
        "slug":           slug[:191],
        "description":    desc[:4000]  or None,
        "logo_url":       logo[:500]   if logo else None,
        "contact_phone":  contact_phone or None,
        "address_line":   address_line  or None,
        "ward":           ward           or None,
        "district":       district       or None,
        "province":       province       or None,
        "total_products": total,
        "status":         "active",
    }

def db_insert_store(data: dict) -> int:
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        INSERT INTO stores (
            store_code,store_name,slug,description,logo_url,
            contact_phone,address_line,ward,district,province,
            total_products,status,created_at,updated_at
        )
        OUTPUT INSERTED.store_id
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,GETDATE(),GETDATE())
    """,
    data["store_code"], data["store_name"], data["slug"],
    data["description"], data["logo_url"], data["contact_phone"],
    data["address_line"], data["ward"], data["district"], data["province"],
    data["total_products"], data["status"])
    sid = cur.fetchone()[0]; con.commit(); con.close()
    return sid

# ─── Crawl danh sách link sản phẩm ──────────────────────────
async def get_product_links(page) -> list:
    hrefs = set()
    for js_var in ["window.__LZD_P_DATA__", "window.__init_data__"]:
        try:
            raw = await page.evaluate(f"JSON.stringify({js_var} || null)")
            if raw:
                hrefs.update(re.findall(
                    r'"(https?://www\.lazada\.vn/products?/[^"]+\.html)"', raw
                ))
        except Exception:
            pass
    if not hrefs:
        for c in await page.query_selector_all(
                "a[href*='/products/'], a[href*='lazada.vn/products']"):
            h = await c.get_attribute("href") or ""
            if ".html" in h:
                h = ("https:" + h) if h.startswith("//") else h
                hrefs.add(h.split("?")[0])
    return list(hrefs)

# ─── Crawl 1 sản phẩm ────────────────────────────────────────
async def crawl_product(page, url: str, store_id: int, category_id: int):
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(2)
    await check_blocked(page)

    name = price = sku = desc = ""
    sold = 0; images = []

    try:
        raw = await page.evaluate("JSON.stringify(window.__init_data__ || {})")
        m = re.search(r'"subject"\s*:\s*"([^"]+)"', raw)
        if m: name = m.group(1)

        prices = re.findall(r'"price"\s*:\s*"([\d,]+)"', raw)
        if prices: price = float(prices[0].replace(",", ""))

        m2 = re.search(r'"salesCountShow"\s*:\s*"([^"]+)"', raw)
        if m2: sold = to_int(m2.group(1))

        m3 = re.search(r'"skuId"\s*:\s*"(\d+)"', raw)
        if m3: sku = m3.group(1)[:50]

        m4 = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        if m4:
            try: desc = m4.group(1).encode().decode("unicode_escape")
            except Exception: desc = m4.group(1)

        seen = set()
        for u in re.findall(
                r'(https://img\.lazcdn\.com[^\\"<>]+\.(?:jpg|png|webp))', raw):
            u2 = re.sub(r'_\d+x\d+[^.]*', '', u)
            if u2 not in seen:
                seen.add(u2); images.append(u2)
    except Exception:
        pass

    # DOM fallback
    if not name:
        name = await el_text(page,
            "[class*='pdp-product-title']", "[class*='title--wrap']", "h1",
            default="Unknown Product"
        )
    if not price:
        price = to_float((await el_text(page,"[class*='pdp-price']","0")).split("–")[0])
    if not sold:
        sold = to_int(await el_text(page, "[class*='sold']", default="0"))
    if not images:
        for el in await page.query_selector_all(
                "[class*='gallery'] img,[class*='item-gallery'] img"):
            src = await el.get_attribute("src") or await el.get_attribute("data-src") or ""
            if "lazcdn" in src and src not in images:
                images.append(src)

    if not sku:
        mu = re.search(r"-s(\d+)\.html", url)
        sku = mu.group(1)[:50] if mu else str(int(time.time()))[-10:]

    ms = re.search(r"lazada\.vn/products?/(.+?)(?:\?|$)", url)
    slug = re.sub(r"-i\d+-s\d+", "", ms.group(1) if ms else name)[:191]

    product = {
        "store_id": store_id, "category_id": category_id,
        "sku": sku, "product_name": name[:200], "slug": slug,
        "description": desc[:8000] or None,
        "price": float(price), "stock_quantity": 0,
        "sold_quantity": int(sold), "status": "active",
    }
    img_records = [
        {"image_url": u[:500], "alt_text": name[:255],
         "display_order": i, "is_primary": 1 if i == 0 else 0}
        for i, u in enumerate(images[:20])
    ]
    return product, img_records

def db_insert_product(product: dict, images: list) -> int:
    con = get_conn(); cur = con.cursor()
    cur.execute("""
        INSERT INTO products (
            store_id,category_id,sku,product_name,slug,description,
            price,stock_quantity,sold_quantity,status,created_at,updated_at
        )
        OUTPUT INSERTED.product_id
        VALUES (?,?,?,?,?,?,?,?,?,?,GETDATE(),GETDATE())
    """,
    product["store_id"], product["category_id"], product["sku"],
    product["product_name"], product["slug"], product["description"],
    product["price"], product["stock_quantity"],
    product["sold_quantity"], product["status"])
    pid = cur.fetchone()[0]
    for img in images:
        cur.execute("""
            INSERT INTO product_images
                (product_id,image_url,alt_text,display_order,is_primary,created_at,updated_at)
            VALUES (?,?,?,?,?,GETDATE(),GETDATE())
        """, pid, img["image_url"], img["alt_text"],
             img["display_order"], img["is_primary"])
    con.commit(); con.close()
    return pid

# ─── MAIN ────────────────────────────────────────────────────
async def main():
    # Kiểm tra DB trước
    try:
        con = get_conn(); con.close()
        print(f"✓ Kết nối DB thành công: {_SERVER}/{_DATABASE}")
    except Exception as e:
        print(f"✗ Lỗi kết nối DB: {e}")
        return

    # Đọc danh sách URL
    try:
        url_list = load_urls()
    except Exception as e:
        print(f"✗ {e}"); return

    print(f"✓ Đọc được {len(url_list)} shop từ urls.xlsx\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox", "--disable-infobars"]
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
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )

        for idx, row in enumerate(url_list, 1):
            shop_url    = row["shop_url"].rstrip("/") + "/"
            category_id = row["category_id"]

            print("═"*60)
            print(f"[SHOP {idx}/{len(url_list)}] {shop_url}")
            print("═"*60)

            try:
                shop_data = await crawl_shop(page, shop_url)
                print(f"  Tên    : {shop_data['store_name']}")
                print(f"  Tổng sp: {shop_data['total_products']}")
                store_id = db_insert_store(shop_data)
                print(f"  ✓ DB   : store_id = {store_id}")
            except Exception as e:
                print(f"  ✗ Lỗi shop: {e}"); continue

            done = 0; page_num = 1; empty_cnt = 0

            while True:
                listing_url = f"{shop_url}?page={page_num}"
                print(f"\n  📄 Trang {page_num}")

                try:
                    await page.goto(listing_url, wait_until="networkidle", timeout=60000)
                    await asyncio.sleep(3)
                    await check_blocked(page)
                    links = await get_product_links(page)
                except Exception as e:
                    print(f"     ✗ Lỗi load trang: {e}"); break

                if not links:
                    empty_cnt += 1
                    if empty_cnt >= 2: print("     → Hết sản phẩm."); break
                    page_num += 1; rand_sleep(2, 4); continue

                empty_cnt = 0
                print(f"     → {len(links)} sản phẩm")

                for link in links:
                    try:
                        print(f"     [{done+1:>4}] {link[:65]}")
                        product, imgs = await crawl_product(page, link, store_id, category_id)
                        pid = db_insert_product(product, imgs)
                        print(f"            ✓ {product['product_name'][:40]}")
                        print(f"              {product['price']:,.0f}đ | bán:{product['sold_quantity']} | ảnh:{len(imgs)} | id={pid}")
                        done += 1
                    except Exception as e:
                        print(f"            ✗ {e}")
                    rand_sleep(1.5, 3.5)

                page_num += 1
                rand_sleep(2, 5)

            print(f"\n  ✅ Shop này: {done} sản phẩm\n")

        await browser.close()

    print("\n" + "═"*60)
    print("✅ HOÀN THÀNH TẤT CẢ!")
    print("═"*60)

if __name__ == "__main__":
    asyncio.run(main())