from extensions import db
from models.order import Order
from models.order_item import OrderItem
from models.order_status_history import OrderStatusHistory
from models.voucher import Voucher, OrderVoucher
from models.product import Product
from models.product_image import ProductImage
from models.store import Store
from models.shipment import Shipment
from models.cart import Cart
from models.cart_item import CartItem
from datetime import datetime
from nanoid import generate
import pytz


class OrderService:

    # API 34: POST /api/v1/orders — Place Order (TRANSACTION)
    @staticmethod
    def place_order(customer_id, store_id, items, recipient_name, recipient_phone,
                    shipping_address_line, shipping_province, shipping_ward=None,
                    shipping_district=None, payment_method='COD', customer_note=None,
                    address_id=None, voucher_code=None):
        try:
            utc = pytz.UTC
            now = datetime.now(utc)

            # === 1. Verify tất cả product thuộc store_id, status='ACTIVE' ===
            product_ids = [item['product_id'] for item in items]
            products = db.session.query(Product).filter(
                Product.product_id.in_(product_ids),
                Product.store_id == store_id,
                Product.status == 'ACTIVE',
                Product.deleted_at.is_(None)
            ).all()

            if len(products) != len(product_ids):
                found_ids = {p.product_id for p in products}
                missing = [pid for pid in product_ids if pid not in found_ids]
                return {
                    'success': False,
                    'message': f'Sản phẩm không hợp lệ hoặc không thuộc cửa hàng: {missing}'
                }, 400

            product_map = {p.product_id: p for p in products}
            qty_map = {item['product_id']: item['quantity'] for item in items}

            # === 2. Check stock ===
            for pid, qty in qty_map.items():
                product = product_map[pid]
                if product.stock_quantity < qty:
                    return {
                        'success': False,
                        'message': f'Không đủ hàng cho "{product.product_name}". Tồn kho: {product.stock_quantity}, yêu cầu: {qty}'
                    }, 400

            # === 3. Tính subtotal ===
            subtotal = sum(float(product_map[pid].price) * qty for pid, qty in qty_map.items())

            # === 4. Xử lý voucher (nếu có) ===
            discount_amount = 0
            voucher = None
            if voucher_code:
                voucher = db.session.query(Voucher).filter(
                    Voucher.voucher_code == voucher_code,
                    Voucher.status == 'ACTIVE',
                    Voucher.deleted_at.is_(None)
                ).first()

                if not voucher:
                    return {'success': False, 'message': 'Voucher không hợp lệ'}, 400

                if voucher.ends_at and voucher.ends_at < now:
                    return {'success': False, 'message': 'Voucher đã hết hạn'}, 400

                if voucher.starts_at and voucher.starts_at > now:
                    return {'success': False, 'message': 'Voucher chưa bắt đầu'}, 400

                if voucher.usage_limit and voucher.used_count >= voucher.usage_limit:
                    return {'success': False, 'message': 'Voucher đã hết lượt sử dụng'}, 400

                if voucher.min_order_amount and subtotal < float(voucher.min_order_amount):
                    return {
                        'success': False,
                        'message': f'Đơn hàng tối thiểu {voucher.min_order_amount} để dùng voucher này'
                    }, 400

                # Kiểm tra per-customer limit
                if voucher.per_customer_limit:
                    customer_usage = db.session.query(OrderVoucher).join(
                        Order, Order.order_id == OrderVoucher.order_id
                    ).filter(
                        OrderVoucher.voucher_id == voucher.voucher_id,
                        Order.customer_id == customer_id,
                        Order.order_status != 'CANCELLED'
                    ).count()

                    if customer_usage >= voucher.per_customer_limit:
                        return {'success': False, 'message': 'Bạn đã sử dụng hết lượt voucher này'}, 400

                # Tính discount
                if voucher.discount_type == 'PERCENT':
                    discount_amount = subtotal * float(voucher.discount_value) / 100
                    if voucher.max_discount_amount:
                        discount_amount = min(discount_amount, float(voucher.max_discount_amount))
                else:  # FIXED
                    discount_amount = float(voucher.discount_value)

                discount_amount = min(discount_amount, subtotal)

            # === 5. Tính total ===
            shipping_fee = 0
            total_amount = subtotal - discount_amount + shipping_fee

            # === 6. INSERT order ===
            order_code = f"ORD-{now.strftime('%Y%m%d')}-{generate(size=8).upper()}"

            order = Order(
                customer_id=customer_id,
                store_id=store_id,
                order_code=order_code,
                order_status='PENDING',
                recipient_name=recipient_name,
                recipient_phone=recipient_phone,
                shipping_address_line=shipping_address_line,
                shipping_ward=shipping_ward,
                shipping_district=shipping_district,
                shipping_province=shipping_province,
                payment_method=payment_method,
                customer_note=customer_note,
                subtotal=subtotal,
                discount_amount=discount_amount,
                shipping_fee=shipping_fee,
                total_amount=total_amount,
                created_at=now,
                updated_at=now
            )
            db.session.add(order)
            db.session.flush()

            # === 7. INSERT order_items (snapshot) ===
            for pid, qty in qty_map.items():
                product = product_map[pid]
                # Lấy primary image
                primary_img = db.session.query(ProductImage.image_url).filter(
                    ProductImage.product_id == pid,
                    ProductImage.is_primary == True
                ).first()

                oi = OrderItem(
                    order_id=order.order_id,
                    product_id=pid,
                    quantity=qty,
                    unit_price=product.price,
                    product_name_snapshot=product.product_name,
                    product_image_url_snapshot=primary_img[0] if primary_img else None,
                    created_at=now,
                    updated_at=now
                )
                db.session.add(oi)

            # === 8. UPDATE stock ===
            for pid, qty in qty_map.items():
                product = product_map[pid]
                product.stock_quantity -= qty
                product.sold_quantity = (product.sold_quantity or 0) + qty
                product.updated_at = now

            # === 9. INSERT status history ===
            history = OrderStatusHistory(
                order_id=order.order_id,
                prev_status=None,
                new_status='PENDING',
                changed_by=customer_id,
                created_at=now
            )
            db.session.add(history)

            # === 10. Voucher: insert order_voucher, update used_count ===
            if voucher:
                ov = OrderVoucher(
                    order_id=order.order_id,
                    voucher_id=voucher.voucher_id,
                    discount_amount=discount_amount,
                    created_at=now
                )
                db.session.add(ov)
                voucher.used_count = (voucher.used_count or 0) + 1
                voucher.updated_at = now

            # === 11. Xóa cart_items tương ứng ===
            cart = db.session.query(Cart).filter(Cart.customer_id == customer_id).first()
            if cart:
                db.session.query(CartItem).filter(
                    CartItem.cart_id == cart.cart_id,
                    CartItem.product_id.in_(product_ids)
                ).delete(synchronize_session='fetch')

            db.session.commit()

            return {
                'success': True,
                'data': {
                    'order_id': order.order_id,
                    'order_code': order.order_code,
                    'order_status': order.order_status,
                    'total_amount': float(order.total_amount),
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            raise e

    # API 35: GET /api/v1/orders — List My Orders
    @staticmethod
    def list_my_orders(customer_id, status=None, page=1, limit=20):
        try:
            offset = (page - 1) * limit

            query = db.session.query(Order).filter(
                Order.customer_id == customer_id,
                Order.deleted_at.is_(None)
            )

            if status:
                query = query.filter(Order.order_status == status)

            total_items = query.count()
            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0

            orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

            orders_list = []
            for o in orders:
                # Lấy first item (snapshot)
                first_item = db.session.query(OrderItem.product_name_snapshot).filter(
                    OrderItem.order_id == o.order_id
                ).first()

                # Lấy store name
                store = db.session.query(Store.store_name).filter(
                    Store.store_id == o.store_id
                ).first()

                orders_list.append({
                    'order_id': o.order_id,
                    'order_code': o.order_code,
                    'order_status': o.order_status,
                    'total_amount': float(o.total_amount),
                    'created_at': o.created_at.isoformat() if o.created_at else None,
                    'store_name': store[0] if store else None,
                    'first_item': first_item[0] if first_item else None,
                })

            return {
                'success': True,
                'data': {
                    'orders': orders_list,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_items': total_items,
                        'total_pages': total_pages,
                    }
                }
            }, 200

        except Exception as e:
            raise e

    # API 36: GET /api/v1/orders/:id — Get Order Detail
    @staticmethod
    def get_order_detail(customer_id, order_id):
        try:
            order = db.session.query(Order).filter(
                Order.order_id == order_id,
                Order.deleted_at.is_(None)
            ).first()

            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404

            # Verify ownership
            if order.customer_id != customer_id:
                return {'success': False, 'message': 'Không có quyền xem đơn hàng này'}, 403

            # Order items
            items = db.session.query(OrderItem).filter(
                OrderItem.order_id == order_id
            ).all()

            items_list = [{
                'order_item_id': oi.order_item_id,
                'product_id': oi.product_id,
                'quantity': oi.quantity,
                'unit_price': float(oi.unit_price),
                'product_name_snapshot': oi.product_name_snapshot,
                'product_image_url_snapshot': oi.product_image_url_snapshot,
            } for oi in items]

            # Store info
            store = db.session.query(Store).filter(Store.store_id == order.store_id).first()
            store_info = {
                'store_name': store.store_name if store else None,
                'logo_url': store.logo_url if store else None,
            }

            # Shipment (LEFT JOIN)
            shipment = db.session.query(Shipment).filter(
                Shipment.order_id == order_id
            ).first()

            shipment_info = None
            if shipment:
                shipment_info = {
                    'status': shipment.status,
                    'tracking_code': shipment.tracking_code,
                    'carrier': shipment.carrier,
                    'shipped_at': shipment.shipped_at.isoformat() if shipment.shipped_at else None,
                    'delivered_at': shipment.delivered_at.isoformat() if shipment.delivered_at else None,
                }

            return {
                'success': True,
                'data': {
                    'order_id': order.order_id,
                    'order_code': order.order_code,
                    'order_status': order.order_status,
                    'recipient_name': order.recipient_name,
                    'recipient_phone': order.recipient_phone,
                    'shipping_address_line': order.shipping_address_line,
                    'shipping_ward': order.shipping_ward,
                    'shipping_district': order.shipping_district,
                    'shipping_province': order.shipping_province,
                    'payment_method': order.payment_method,
                    'customer_note': order.customer_note,
                    'subtotal': float(order.subtotal),
                    'discount_amount': float(order.discount_amount),
                    'shipping_fee': float(order.shipping_fee),
                    'total_amount': float(order.total_amount),
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'items': items_list,
                    'store': store_info,
                    'shipment': shipment_info,
                }
            }, 200

        except Exception as e:
            raise e

    # API 37: POST /api/v1/orders/:id/cancel — Cancel Order
    @staticmethod
    def cancel_order(customer_id, order_id, cancel_reason=None):
        try:
            order = db.session.query(Order).filter(
                Order.order_id == order_id,
                Order.deleted_at.is_(None)
            ).first()

            if not order:
                return {'success': False, 'message': 'Đơn hàng không tồn tại'}, 404

            # Verify ownership
            if order.customer_id != customer_id:
                return {'success': False, 'message': 'Không có quyền hủy đơn hàng này'}, 403

            # Chỉ hủy được khi status = PENDING
            if order.order_status != 'PENDING':
                return {'success': False, 'message': 'Không thể hủy đơn đã xử lý'}, 400

            utc = pytz.UTC
            now = datetime.now(utc)

            # Cập nhật order
            order.order_status = 'CANCELLED'
            order.cancelled_by_user_id = customer_id
            order.cancel_reason = cancel_reason
            order.cancelled_at = now
            order.updated_at = now

            # INSERT status history
            history = OrderStatusHistory(
                order_id=order.order_id,
                prev_status='PENDING',
                new_status='CANCELLED',
                changed_by=customer_id,
                note=cancel_reason,
                created_at=now
            )
            db.session.add(history)

            # Hoàn stock
            order_items = db.session.query(OrderItem).filter(
                OrderItem.order_id == order_id
            ).all()

            for oi in order_items:
                product = db.session.query(Product).filter(
                    Product.product_id == oi.product_id
                ).first()
                if product:
                    product.stock_quantity += oi.quantity
                    product.sold_quantity = max((product.sold_quantity or 0) - oi.quantity, 0)
                    product.updated_at = now

            db.session.commit()

            return {'success': True, 'message': 'Đã hủy đơn'}, 200

        except Exception as e:
            db.session.rollback()
            raise e
