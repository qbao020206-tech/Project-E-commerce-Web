from models.category import Category


class CategoryService:

    # API 16: GET /api/v1/categories | Public
    @staticmethod
    def get_all_categories():
        try:
            # Step 1 — Query top-level categories (parent_category_id IS NULL)
            top_level = Category.query.filter(
                Category.parent_category_id.is_(None),
                Category.status == 'ACTIVE',
                Category.deleted_at.is_(None)
            ).order_by(Category.display_order.asc(), Category.category_id.asc()).all()

            # Step 2 — Query toàn bộ sub-categories
            sub_categories = Category.query.filter(
                Category.parent_category_id.isnot(None),
                Category.status == 'ACTIVE',
                Category.deleted_at.is_(None)
            ).order_by(Category.display_order.asc()).all()

            # Step 3 — Build tree ở application code (không dùng recursive SQL)
            sub_map = {}
            for sub in sub_categories:
                pid = sub.parent_category_id
                if pid not in sub_map:
                    sub_map[pid] = []
                sub_map[pid].append({
                    'category_id': sub.category_id,
                    'category_name': sub.category_name,
                    'slug': sub.slug,
                    'icon_url': sub.icon_url,
                    'display_order': sub.display_order,
                })

            categories = []
            for cat in top_level:
                categories.append({
                    'category_id': cat.category_id,
                    'category_name': cat.category_name,
                    'slug': cat.slug,
                    'icon_url': cat.icon_url,
                    'display_order': cat.display_order,
                    'children': sub_map.get(cat.category_id, []),
                })

            return {
                'success': True,
                'data': {
                    'categories': categories
                }
            }, 200

        except Exception as e:
            raise e

    # API 17: GET /api/v1/categories/:id | Public
    @staticmethod
    def get_category_detail(category_id):
        try:
            # Query 1 — Category chính kèm parent (LEFT JOIN)
            category = Category.query.filter(
                Category.category_id == category_id,
                Category.status == 'ACTIVE',
                Category.deleted_at.is_(None)
            ).first()

            if not category:
                return {'success': False, 'message': 'Danh mục không tồn tại'}, 404

            # Build parent object nếu có
            parent = None
            if category.parent_category_id:
                parent_cat = Category.query.filter(
                    Category.category_id == category.parent_category_id,
                    Category.status == 'ACTIVE',
                    Category.deleted_at.is_(None)
                ).first()
                if parent_cat:
                    parent = {
                        'category_id': parent_cat.category_id,
                        'category_name': parent_cat.category_name,
                        'slug': parent_cat.slug,
                    }

            # Query 2 — Sub-categories của category này
            subs = Category.query.filter(
                Category.parent_category_id == category_id,
                Category.status == 'ACTIVE',
                Category.deleted_at.is_(None)
            ).order_by(Category.display_order.asc()).all()

            children = [
                {
                    'category_id': s.category_id,
                    'category_name': s.category_name,
                    'slug': s.slug,
                    'icon_url': s.icon_url,
                    'display_order': s.display_order,
                }
                for s in subs
            ]

            return {
                'success': True,
                'data': {
                    'category_id': category.category_id,
                    'category_name': category.category_name,
                    'slug': category.slug,
                    'description': category.description,
                    'icon_url': category.icon_url,
                    'display_order': category.display_order,
                    'parent': parent,   # None nếu là top-level
                    'children': children,
                }
            }, 200

        except Exception as e:
            raise e