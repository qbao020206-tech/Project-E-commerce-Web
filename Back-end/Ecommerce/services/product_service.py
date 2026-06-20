from extensions import db
from models.product import Product
from models.product_image import ProductImage
from models.review import Review
from models.store import Store
from models.category import Category
from models.user import User
from sqlalchemy import func, and_

class ProductService:

    @staticmethod
    def get_products_list(page=1, limit=20, keyword=None, category_id=None,
                         store_id=None, min_price=None, max_price=None,
                         sort_by='created_at', sort_order='DESC'):
        """Lấy danh sách sản phẩm với bộ lọc và phân trang"""
        try:
            offset = (page - 1) * limit

            # Base query
            query = db.session.query(
                Product.product_id,
                Product.product_name,
                Product.slug,
                Product.price,
                Product.stock_quantity,
                Product.sold_quantity,
                Product.status,
                Product.created_at,
                Category.category_id,
                Category.category_name,
                Store.store_id,
                Store.store_name,
                Store.logo_url.label('store_logo'),
                ProductImage.image_url.label('primary_image_url'),
                func.round(func.avg(func.cast(Review.rating, db.Float)), 1).label('avg_rating'),
                func.count(func.distinct(Review.review_id)).label('review_count')
            ).join(Store, Product.store_id == Store.store_id).join(
                Category, Product.category_id == Category.category_id
            ).outerjoin(
                ProductImage, and_(
                    ProductImage.product_id == Product.product_id,
                    ProductImage.is_primary == True
                )
            ).outerjoin(
                Review, and_(
                    Review.product_id == Product.product_id,
                    Review.status == 'VISIBLE'
                )
            )

            # Filter by product status and deleted_at
            query = query.filter(
                Product.status == 'ACTIVE',
                Product.deleted_at.is_(None)
            )

            # Filter by store status and deleted_at
            query = query.filter(
                Store.status == 'ACTIVE',
                Store.deleted_at.is_(None)
            )

            # Apply filters
            if keyword:
                query = query.filter(Product.product_name.ilike(f'%{keyword}%'))

            if category_id:
                query = query.filter(Product.category_id == category_id)

            if store_id:
                query = query.filter(Product.store_id == store_id)

            if min_price is not None:
                query = query.filter(Product.price >= min_price)

            if max_price is not None:
                query = query.filter(Product.price <= max_price)

            # Group by
            query = query.group_by(
                Product.product_id, Product.product_name, Product.slug,
                Product.price, Product.stock_quantity, Product.sold_quantity,
                Product.status, Product.created_at,
                Category.category_id, Category.category_name,
                Store.store_id, Store.store_name, Store.logo_url,
                ProductImage.image_url
            )

            # Sort
            if sort_by == 'price':
                sort_column = Product.price
            elif sort_by == 'sold_quantity':
                sort_column = Product.sold_quantity
            else:
                sort_column = Product.created_at

            if sort_order.upper() == 'ASC':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Get total count before pagination
            total_items = query.count()
            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0

            # Pagination
            products = query.offset(offset).limit(limit).all()

            # Format response
            products_list = []
            for product in products:
                products_list.append({
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'slug': product.slug,
                    'price': float(product.price),
                    'stock_quantity': product.stock_quantity,
                    'sold_quantity': product.sold_quantity,
                    'primary_image_url': product.primary_image_url,
                    'avg_rating': float(product.avg_rating) if product.avg_rating else 0,
                    'review_count': product.review_count or 0,
                    'category': {
                        'category_id': product.category_id,
                        'category_name': product.category_name
                    },
                    'store': {
                        'store_id': product.store_id,
                        'store_name': product.store_name,
                        'store_logo': product.store_logo
                    }
                })

            return {
                'success': True,
                'data': {
                    'products': products_list,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_items': total_items,
                        'total_pages': total_pages
                    }
                }
            }, 200
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500

    @staticmethod
    def get_product_detail(product_id):
        """Lấy chi tiết 1 sản phẩm"""
        try:
            product = Product.query.filter(
                Product.product_id == product_id,
                Product.deleted_at.is_(None),
                Product.status == 'ACTIVE'
            ).first()

            if not product:
                return {'success': False, 'message': 'Sản phẩm không tồn tại hoặc đã bị ẩn.'}, 404

            # Check store status
            store = Store.query.filter(
                Store.store_id == product.store_id,
                Store.deleted_at.is_(None),
                Store.status == 'ACTIVE'
            ).first()

            if not store:
                return {'success': False, 'message': 'Sản phẩm không tồn tại hoặc đã bị ẩn.'}, 404

            # Get category with parent
            category = Category.query.get(product.category_id)
            parent_category = None
            if category and category.parent_category_id:
                parent_category = Category.query.get(category.parent_category_id)

            # Get all images
            images = ProductImage.query.filter(
                ProductImage.product_id == product_id
            ).order_by(ProductImage.display_order.asc()).all()

            # Get rating statistics
            reviews_data = db.session.query(
                func.round(func.avg(func.cast(Review.rating, db.Float)), 1).label('avg_rating'),
                func.count(Review.review_id).label('review_count'),
                func.sum(func.case((Review.rating == 5, 1), else_=0)).label('rating_5'),
                func.sum(func.case((Review.rating == 4, 1), else_=0)).label('rating_4'),
                func.sum(func.case((Review.rating == 3, 1), else_=0)).label('rating_3'),
                func.sum(func.case((Review.rating == 2, 1), else_=0)).label('rating_2'),
                func.sum(func.case((Review.rating == 1, 1), else_=0)).label('rating_1')
            ).filter(
                Review.product_id == product_id,
                Review.status == 'VISIBLE'
            ).first()

            # Format response
            response = {
                'success': True,
                'data': {
                    'product_id': product.product_id,
                    'product_name': product.product_name,
                    'slug': product.slug,
                    'sku': product.sku,
                    'description': product.description,
                    'price': float(product.price),
                    'stock_quantity': product.stock_quantity,
                    'sold_quantity': product.sold_quantity,
                    'status': product.status,
                    'created_at': product.created_at.isoformat() if product.created_at else None,
                    'updated_at': product.updated_at.isoformat() if product.updated_at else None,
                    'images': [
                        {
                            'image_url': img.image_url,
                            'alt_text': img.alt_text,
                            'display_order': img.display_order,
                            'is_primary': img.is_primary
                        }
                        for img in images
                    ],
                    'category': {
                        'category_id': category.category_id,
                        'category_name': category.category_name,
                        'slug': category.slug,
                        'parent_category': {
                            'category_id': parent_category.category_id,
                            'category_name': parent_category.category_name
                        } if parent_category else None
                    },
                    'store': {
                        'store_id': store.store_id,
                        'store_name': store.store_name,
                        'slug': store.slug,
                        'store_logo': store.logo_url,
                        'contact_phone': store.contact_phone,
                        'province': store.province,
                        'total_products': store.total_products
                    },
                    'rating_summary': {
                        'avg_rating': float(reviews_data.avg_rating) if reviews_data.avg_rating else 0,
                        'review_count': reviews_data.review_count or 0,
                        'distribution': {
                            '5': reviews_data.rating_5 or 0,
                            '4': reviews_data.rating_4 or 0,
                            '3': reviews_data.rating_3 or 0,
                            '2': reviews_data.rating_2 or 0,
                            '1': reviews_data.rating_1 or 0
                        }
                    }
                }
            }

            return response, 200
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500

    @staticmethod
    def get_product_reviews(product_id, page=1, limit=10, rating=None,
                           sort_by='created_at', sort_order='DESC'):
        """Lấy danh sách đánh giá của sản phẩm"""
        try:
            # Check if product exists and is active
            product = Product.query.filter(
                Product.product_id == product_id,
                Product.status == 'ACTIVE',
                Product.deleted_at.is_(None)
            ).first()

            if not product:
                return {'success': False, 'message': 'Sản phẩm không tồn tại hoặc đã bị ẩn.'}, 404

            offset = (page - 1) * limit

            # Base query
            query = db.session.query(
                Review.review_id,
                Review.rating,
                Review.comment,
                Review.created_at,
                Review.customer_id
            ).filter(
                Review.product_id == product_id,
                Review.status == 'VISIBLE'
            )

            # Filter by rating if provided
            if rating:
                query = query.filter(Review.rating == rating)

            # Sort
            if sort_by == 'rating':
                sort_column = Review.rating
            else:
                sort_column = Review.created_at

            if sort_order.upper() == 'ASC':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Count total
            count_query = db.session.query(func.count(Review.review_id)).filter(
                Review.product_id == product_id,
                Review.status == 'VISIBLE'
            )
            if rating:
                count_query = count_query.filter(Review.rating == rating)

            total_items = count_query.scalar() or 0
            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0

            # Get reviews
            reviews = query.offset(offset).limit(limit).all()

            # Format response
            reviews_list = []
            for review in reviews:
                # Get user info
                reviewer = User.query.get(review.customer_id)

                reviews_list.append({
                    'review_id': review.review_id,
                    'rating': review.rating,
                    'comment': review.comment,
                    'created_at': review.created_at.isoformat() if review.created_at else None,
                    'reviewer': {
                        'user_id': review.customer_id,
                        'full_name': reviewer.full_name if reviewer else 'Unknown',
                        'avatar_url': reviewer.avatar_url if reviewer else None
                    }
                })

            return {
                'success': True,
                'data': {
                    'product_id': product_id,
                    'reviews': reviews_list,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_items': total_items,
                        'total_pages': total_pages
                    }
                }
            }, 200
        except Exception as e:
            return {'success': False, 'message': str(e)}, 500
