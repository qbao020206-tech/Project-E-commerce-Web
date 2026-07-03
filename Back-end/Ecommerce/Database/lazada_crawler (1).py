#!/usr/bin/env python3
"""
lazada_crawler.py — bản nâng cấp từ Database/Lazada.py
─────────────────────────────────────────────────────────────────
So với Lazada.py gốc, bản này sửa các vấn đề sau:

  1. status LUÔN viết hoa 'ACTIVE' (bug gốc dùng 'active' chữ thường khiến
     CK_stores_status / CK_products_status reject MỌI insert).
  2. price không còn có thể "vô tình" = 0 → dùng Faker fallback hợp lý khi
     crawl thật sự không lấy được giá, thay vì để giá trị vi phạm CHECK (price > 0).
  3. stock_quantity không còn hardcode = 0 → Lazada không công khai tồn kho thật
     trên trang public nên trường này LUÔN là số mô phỏng (Faker), có chú thích
     rõ trong code để không ai hiểu nhầm đây là "lỗi crawl".
  4. Idempotent: chạy lại script, hoặc crawl lại đúng 1 shop đã có, KHÔNG tạo
     trùng store (check theo store_code) hay trùng product (check theo
     store_id + sku) → không còn dính lỗi UNIQUE constraint khi chạy nhiều lần.
  5. Mỗi store mới tự động có 1 user 'seller' + role SELLER + quyền OWNER
     trong user_stores → store không còn "vô chủ", test được luôn API phía Seller.
  6. category lấy theo TÊN (cột category_name trong urls.xlsx) thay vì ID cứng,
     tra theo bảng categories đã seed sẵn bằng seed_categories.py — không cần
     đoán category_id IDENTITY là số mấy.
  7. Sản phẩm không crawl được ảnh nào → gắn 1 ảnh placeholder thay vì để
     trống hẳn, tránh vỡ layout storefront.

Cài đặt (ngoài requirement.txt hiện có của project):
    pip install playwright pyodbc python-dotenv openpyxl pandas faker python-slugify nanoid
    playwright install chromium

Chuẩn bị trước khi chạy:
    1. Đã chạy SQLServer_Nhom2.sql (có DB + bảng + 4 role).
    2. Chạy:  python seed_categories.py
    3. Tạo/sửa file urls.xlsx (cùng thư mục) với 2 cột:
           shop_url                              | category_name
           https://www.lazada.vn/shop/abc/        | Điện thoại smartphone
           https://www.lazada.vn/shop/xyz/        | Thời trang nam
       category_name PHẢI khớp (không phân biệt hoa/thường) tên category CON
       đã seed ở bước 2 — chạy seed_categories.py để xem danh sách đầy đủ.

Chạy:
    python lazada_crawler.py
"""

import asyncio
import re
import time
import random
import unicodedata
from pathlib import Path

import pandas as pd
from slugify import slugify
from playwright.async_api import async_playwright

from db_seed_helpers import (
    fake,
    fallback_price,
    fallback_stock,
    fallback_description,
    placeholder_image_url,
    unique_slug,
    safe_store_code,
    find_category_id_by_name,
    get_or_create_store_with_owner,
    find_existing_product_id,
    insert_product_with_images,
    get_conn,
)

BASE_DIR = Path(__file__).resolve().parent


# ─── Đọc danh sách URL + category_name từ Excel ─────────────────────────────
def load_urls() -> list:
    xlsx = BASE_DIR / "urls.xlsx"
    if not xlsx.exists():
        raise FileNotFoundError(
            "Không tìm thấy urls.xlsx!\nTạo file với 2 cột: shop_url | category_name "
            "(xem urls_template.xlsx mẫu đi kèm)."
        )
    df = pd.read_excel(xlsx, dtype=str)

    def _normalize_col_name(name: str) -> str:
        clean = str(name).strip()
        clean = unicodedata.normalize("NFKD", clean)
        clean = clean.encode("ascii", "ignore").decode("ascii")
        clean = clean.lower().replace(" ", "_")
        return re.sub(r"[^a-z0-9_]", "", clean)

    col_map = {_normalize_col_name(c): c for c in df.columns}

    shop_col = next((col_map[c] for c in
                      ["shop_url", "shopurl", "url", "url_cua_hang"] if c in col_map), None)
    if not shop_col:
        print(f"  DEBUG – Cột đọc được: {list(col_map.keys())}")
        raise ValueError("Excel thiếu cột 'shop_url'")

    cat_col = next((col_map[c] for c in
                     ["category_name", "categoryname", "category", "danh_muc", "ten_danh_muc"]
                     if c in col_map), None)
    if not cat_col:
        raise ValueError("Excel thiếu cột 'category_name' (vd: 'Thời trang nam') — xem urls_template.xlsx")

    rows = []
    for _, r in df.iterrows():
        url = str(r.get(shop_col, "")).strip().split("?")[0]
        if not url or url in ("nan", "") or url.startswith("#"):
            continue
        cat_name = str(r.get(cat_col, "")).strip()
        if not cat_name or cat_name == "nan":
            print(f"  ⚠ Bỏ qua dòng thiếu category_name: {url}")
            continue
        rows.append({"shop_url": url, "category_name": cat_name})
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
        default=""
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

    # Fallback tên shop NẾU crawl thật không lấy được — làm TRƯỚC khi tính slug
    # để slug fallback cũng dùng tên này (tránh nhiều shop lỗi đụng "unknown-shop").
    if not name:
        name = f"Shop {fake.company()}"

    m = re.search(r"lazada\.vn/shop/([^/?]+)", shop_url)
    base_slug_text = m.group(1) if m else name

    return {
        "store_code":     safe_store_code(base_slug_text),
        "store_name":     name[:150],
        "slug":           unique_slug(base_slug_text),
        "description":    (desc[:4000] if desc else None),
        "logo_url":       logo[:500]   if logo else None,
        "contact_phone":  contact_phone or None,
        "address_line":   address_line  or None,
        "ward":           ward           or None,
        "district":       district       or None,
        "province":       province       or None,
        "total_products": total,
    }


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
async def crawl_product(page, url: str, category_name: str):
    await page.goto(url, wait_until="networkidle", timeout=60000)
    await asyncio.sleep(2)
    await check_blocked(page)

    name = ""
    price = 0.0
    sku = desc = ""
    sold = 0
    images = []

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

    # DOM fallback (vẫn là crawl thật, chỉ đổi nguồn tìm trên trang)
    if not name:
        name = await el_text(page,
            "[class*='pdp-product-title']", "[class*='title--wrap']", "h1",
            default=""
        )
    if not price:
        # Bug gốc: el_text(page, sel, "0") truyền "0" như SELECTOR thứ 2 chứ
        # KHÔNG phải default (default= là keyword-only) → luôn rơi về "" ngầm.
        # Sửa bằng cách dùng đúng default= keyword.
        price_text = await el_text(page, "[class*='pdp-price']", default="")
        price = to_float(price_text.split("–")[0]) if price_text else 0.0
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
        sku = mu.group(1)[:50] if mu else str(int(time.time() * 1000))[-12:]

    # ── Faker / template fallback — CHỈ kích hoạt khi crawl thật KHÔNG lấy được ──
    used_fallback = []
    if not name:
        name = f"{category_name} {fake.word().capitalize()}"
        used_fallback.append("name")
    if price <= 0:
        price = fallback_price()
        used_fallback.append("price")
    if not desc:
        desc = fallback_description(name, category_name)
        used_fallback.append("description")

    ms = re.search(r"lazada\.vn/products?/(.+?)(?:\?|$)", url)
    slug_text = re.sub(r"-i\d+-s\d+", "", ms.group(1) if ms else name)

    product = {
        "sku": sku,
        "product_name": name[:200],
        "slug": unique_slug(slug_text),
        "description": desc[:8000],
        "price": float(price),
        # Lazada KHÔNG công khai tồn kho thật trên trang public — trường này
        # LUÔN là số mô phỏng, không tính vào "used_fallback" vì không phải lỗi.
        "stock_quantity": fallback_stock(),
        "sold_quantity": int(sold),
    }

    img_records = [
        {"image_url": u[:500], "alt_text": name[:255],
         "display_order": i, "is_primary": 1 if i == 0 else 0}
        for i, u in enumerate(images[:20])
    ]
    if not img_records:
        img_records = [{
            "image_url": placeholder_image_url(name),
            "alt_text": name[:255],
            "display_order": 0,
            "is_primary": 1,
        }]
        used_fallback.append("image(placeholder)")

    if used_fallback:
        print(f"            ⚠ Fallback field: {', '.join(used_fallback)}")

    return product, img_records


# ─── Ghi DB: idempotent theo (store_id, sku) ────────────────────────────────
def save_product(conn, store_id: int, category_id: int, product: dict, images: list):
    existing_id = find_existing_product_id(conn, store_id, product["sku"])
    if existing_id:
        return existing_id, False  # đã tồn tại — bỏ qua, không ghi đè giá/tồn kho demo

    pid = insert_product_with_images(conn, store_id, category_id, product, images)
    return pid, True


# ─── MAIN ────────────────────────────────────────────────────
async def main():
    conn = get_conn()
    print("✓ Kết nối DB thành công")

    try:
        url_list = load_urls()
    except Exception as e:
        print(f"✗ {e}")
        conn.close()
        return

    print(f"✓ Đọc được {len(url_list)} shop từ urls.xlsx\n")

    # Resolve category_name → category_id 1 LẦN, fail sớm nếu thiếu category
    # (đỡ tốn công crawl rồi mới phát hiện category sai tên).
    for row in url_list:
        cat_id = find_category_id_by_name(conn, row["category_name"])
        if not cat_id:
            print(f"✗ Không tìm thấy category '{row['category_name']}' trong DB.")
            print("  → Chạy `python seed_categories.py` trước, hoặc sửa lại tên cho khớp.")
            conn.close()
            return
        row["category_id"] = cat_id

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,   # QUAN TRỌNG: False để tránh bị chặn
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

        total_new = 0

        for idx, row in enumerate(url_list, 1):
            shop_url = row["shop_url"].rstrip("/") + "/"
            category_id = row["category_id"]
            category_name = row["category_name"]

            print("═" * 60)
            print(f"[SHOP {idx}/{len(url_list)}] {shop_url}  (category: {category_name})")
            print("═" * 60)

            try:
                shop_data = await crawl_shop(page, shop_url)
                print(f"  Tên    : {shop_data['store_name']}")
                store_id = get_or_create_store_with_owner(conn, shop_data)
                print(f"  ✓ DB   : store_id = {store_id}")
            except Exception as e:
                print(f"  ✗ Lỗi shop: {e}"); continue

            done = 0
            skipped_existing = 0
            page_num = 1
            empty_cnt = 0

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
                    if empty_cnt >= 2:
                        print("     → Hết sản phẩm.")
                        break
                    page_num += 1
                    rand_sleep(2, 4)
                    continue

                empty_cnt = 0
                print(f"     → {len(links)} sản phẩm")

                for link in links:
                    try:
                        print(f"     [{done + skipped_existing + 1:>4}] {link[:65]}")
                        product, imgs = await crawl_product(page, link, category_name)
                        pid, is_new = save_product(conn, store_id, category_id, product, imgs)
                        if is_new:
                            print(f"            ✓ {product['product_name'][:40]} "
                                  f"| {product['price']:,.0f}đ | tồn:{product['stock_quantity']} | id={pid}")
                            done += 1
                        else:
                            print(f"            = đã có sẵn (sku={product['sku']}), bỏ qua")
                            skipped_existing += 1
                    except Exception as e:
                        print(f"            ✗ {e}")
                    rand_sleep(1.5, 3.5)

                page_num += 1
                rand_sleep(2, 5)

            print(f"\n  ✅ Shop này: {done} sản phẩm mới, {skipped_existing} đã có sẵn (bỏ qua)\n")
            total_new += done

        await browser.close()

    conn.close()
    print("\n" + "═" * 60)
    print(f"✅ HOÀN THÀNH! Tổng {total_new} sản phẩm mới được thêm vào DB.")
    print("═" * 60)


if __name__ == "__main__":
    asyncio.run(main())
