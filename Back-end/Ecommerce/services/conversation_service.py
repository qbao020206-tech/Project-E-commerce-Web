from extensions import db
from models.conversation import Conversation
from models.message import Message
from models.store import Store
from models.user import User
from models.user_store import UserStore
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import pytz


class ConversationService:

    # ── Helper: lấy store_id của seller (OWNER) ──────────────────────────────
    @staticmethod
    def _get_seller_store_id(user_id):
        """Trả về store_id nếu user là OWNER, ngược lại trả None."""
        row = (
            db.session.query(UserStore.store_id)
            .filter(
                UserStore.user_id == user_id,
                UserStore.store_member_role == 'OWNER',
                UserStore.is_active == 1
            )
            .first()
        )
        return row.store_id if row else None

    # ── Helper: kiểm tra user có phải participant của conversation không ──────
    @staticmethod
    def _verify_participant(conversation, user_id, seller_store_id=None):
        """
        Trả True nếu user_id là customer của conversation
        HOẶC seller_store_id khớp store_id của conversation.
        """
        if conversation.customer_id == user_id:
            return True
        if seller_store_id and conversation.store_id == seller_store_id:
            return True
        return False

    # ── API 44: GET /api/v1/conversations ────────────────────────────────────
    @staticmethod
    def list_conversations(user_id, roles):
        try:
            is_seller = 'SELLER' in roles
            is_customer = 'CUSTOMER' in roles

            if is_seller:
                seller_store_id = ConversationService._get_seller_store_id(user_id)
                if not seller_store_id:
                    return {'success': False, 'message': 'Bạn chưa tạo cửa hàng'}, 404

            # Dùng raw SQL để JOIN lấy last_message theo đúng đặc tả
            if is_seller:
                sql = text("""
                    SELECT
                        c.conversation_id, c.customer_id, c.store_id, c.order_id,
                        c.status, c.last_message_at, c.created_at,
                        last_msg.message_content AS last_message_preview,
                        last_msg.created_at      AS last_message_at_msg,
                        s.store_name, s.logo_url,
                        u.full_name AS customer_name,
                        u.avatar_url AS customer_avatar
                    FROM conversations c
                    JOIN stores s ON c.store_id = s.store_id
                    JOIN users  u ON c.customer_id = u.user_id
                    OUTER APPLY (
                        SELECT TOP 1 message_content, created_at
                        FROM messages
                        WHERE conversation_id = c.conversation_id
                        ORDER BY created_at DESC
                    ) last_msg
                    WHERE c.store_id = :store_id
                    ORDER BY last_msg.created_at DESC
                """)
                rows = db.session.execute(sql, {'store_id': seller_store_id}).fetchall()
            else:
                # Customer
                sql = text("""
                    SELECT
                        c.conversation_id, c.customer_id, c.store_id, c.order_id,
                        c.status, c.last_message_at, c.created_at,
                        last_msg.message_content AS last_message_preview,
                        last_msg.created_at      AS last_message_at_msg,
                        s.store_name, s.logo_url,
                        u.full_name AS customer_name,
                        u.avatar_url AS customer_avatar
                    FROM conversations c
                    JOIN stores s ON c.store_id = s.store_id
                    JOIN users  u ON c.customer_id = u.user_id
                    OUTER APPLY (
                        SELECT TOP 1 message_content, created_at
                        FROM messages
                        WHERE conversation_id = c.conversation_id
                        ORDER BY created_at DESC
                    ) last_msg
                    WHERE c.customer_id = :uid
                    ORDER BY last_msg.created_at DESC
                """)
                rows = db.session.execute(sql, {'uid': user_id}).fetchall()

            conversations = []
            for r in rows:
                conversations.append({
                    'conversation_id': r.conversation_id,
                    'store': {
                        'store_id': r.store_id,
                        'store_name': r.store_name,
                        'logo_url': r.logo_url,
                    },
                    'customer': {
                        'customer_id': r.customer_id,
                        'customer_name': r.customer_name,
                        'customer_avatar': r.customer_avatar,
                    },
                    'order_id': r.order_id,
                    'last_message_preview': r.last_message_preview,
                    'last_message_at': r.last_message_at_msg.isoformat() if r.last_message_at_msg else None,
                    'status': r.status,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                })

            return {'success': True, 'data': {'conversations': conversations}}, 200

        except Exception as e:
            raise e

    # ── API 45: POST /api/v1/conversations ───────────────────────────────────
    @staticmethod
    def create_conversation(customer_id, store_id, order_id=None):
        try:
            # Kiểm tra store tồn tại và ACTIVE
            store = db.session.query(Store).filter(
                Store.store_id == store_id,
                Store.status == 'ACTIVE',
                Store.deleted_at.is_(None)
            ).first()
            if not store:
                return {'success': False, 'message': 'Cửa hàng không tồn tại hoặc không hoạt động'}, 404

            utc = pytz.UTC
            now = datetime.now(utc)

            # Thử INSERT — nếu vi phạm unique constraint thì trả 200 với conversation cũ
            conv = Conversation(
                customer_id=customer_id,
                store_id=store_id,
                order_id=order_id,
                status='OPEN',
                created_at=now,
                updated_at=now
            )
            db.session.add(conv)
            db.session.flush()  # bắt IntegrityError trước khi commit
            db.session.commit()

            return {
                'success': True,
                'data': ConversationService._conv_to_dict(conv)
            }, 201

        except IntegrityError:
            # Đã tồn tại → trả về conversation hiện tại
            db.session.rollback()
            existing = db.session.query(Conversation).filter(
                Conversation.customer_id == customer_id,
                Conversation.store_id == store_id
            ).first()
            if existing:
                return {
                    'success': True,
                    'data': ConversationService._conv_to_dict(existing)
                }, 200
            return {'success': False, 'message': 'Không thể tạo cuộc trò chuyện'}, 409

        except Exception as e:
            db.session.rollback()
            raise e

    # ── API 46: GET /api/v1/conversations/:id/messages ───────────────────────
    @staticmethod
    def get_messages(conversation_id, user_id, roles, page=1, limit=20):
        try:
            conv = db.session.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            if not conv:
                return {'success': False, 'message': 'Cuộc trò chuyện không tồn tại'}, 404

            # Verify participant
            seller_store_id = None
            if 'Seller' in roles:
                seller_store_id = ConversationService._get_seller_store_id(user_id)

            if not ConversationService._verify_participant(conv, user_id, seller_store_id):
                return {'success': False, 'message': 'Bạn không có quyền xem cuộc trò chuyện này'}, 403

            offset = (page - 1) * limit

            sql_count = text("""
                SELECT COUNT(*) AS total FROM messages WHERE conversation_id = :cid
            """)
            total_items = db.session.execute(sql_count, {'cid': conversation_id}).scalar()

            sql = text("""
                SELECT m.message_id, m.conversation_id, m.sender_user_id,
                       m.message_content, m.is_read, m.read_at, m.created_at,
                       u.full_name AS sender_name, u.avatar_url AS sender_avatar
                FROM messages m
                JOIN users u ON m.sender_user_id = u.user_id
                WHERE m.conversation_id = :cid
                ORDER BY m.created_at DESC
                OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
            """)
            rows = db.session.execute(sql, {
                'cid': conversation_id,
                'offset': offset,
                'limit': limit
            }).fetchall()

            messages = []
            for r in rows:
                messages.append({
                    'message_id': r.message_id,
                    'sender': {
                        'user_id': r.sender_user_id,
                        'full_name': r.sender_name,
                        'avatar_url': r.sender_avatar,
                    },
                    'message_content': r.message_content,
                    'is_read': bool(r.is_read),
                    'read_at': r.read_at.isoformat() if r.read_at else None,
                    'created_at': r.created_at.isoformat() if r.created_at else None,
                })

            total_pages = (total_items + limit - 1) // limit if total_items > 0 else 1

            return {
                'success': True,
                'data': {
                    'messages': messages,
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

    # ── API 47: POST /api/v1/conversations/:id/messages ──────────────────────
    @staticmethod
    def send_message(conversation_id, user_id, roles, message_content):
        try:
            conv = db.session.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            if not conv:
                return {'success': False, 'message': 'Cuộc trò chuyện không tồn tại'}, 404

            # Verify participant
            seller_store_id = None
            if 'Seller' in roles:
                seller_store_id = ConversationService._get_seller_store_id(user_id)

            if not ConversationService._verify_participant(conv, user_id, seller_store_id):
                return {'success': False, 'message': 'Bạn không có quyền gửi tin nhắn trong cuộc trò chuyện này'}, 403

            # Validate nội dung không rỗng / chỉ toàn whitespace
            if not message_content or not message_content.strip():
                return {'success': False, 'message': 'Nội dung tin nhắn không được để trống'}, 400

            utc = pytz.UTC
            now = datetime.now(utc)

            msg = Message(
                conversation_id=conversation_id,
                sender_user_id=user_id,
                message_content=message_content.strip(),
                is_read=0,
                created_at=now,
                updated_at=now
            )
            db.session.add(msg)

            # Cập nhật last_message_at của conversation để đảm bảo nhất quán dữ liệu
            conv.last_message_at = now
            conv.updated_at = now

            db.session.commit()

            return {
                'success': True,
                'data': {
                    'message_id': msg.message_id,
                    'conversation_id': msg.conversation_id,
                    'sender_user_id': msg.sender_user_id,
                    'message_content': msg.message_content,
                    'is_read': bool(msg.is_read),
                    'created_at': msg.created_at.isoformat() if msg.created_at else None,
                }
            }, 201

        except Exception as e:
            db.session.rollback()
            raise e

    # ── API 48: PATCH /api/v1/conversations/:id/read ─────────────────────────
    @staticmethod
    def mark_as_read(conversation_id, user_id, roles):
        try:
            conv = db.session.query(Conversation).filter(
                Conversation.conversation_id == conversation_id
            ).first()
            if not conv:
                return {'success': False, 'message': 'Cuộc trò chuyện không tồn tại'}, 404

            # Verify participant
            seller_store_id = None
            if 'Seller' in roles:
                seller_store_id = ConversationService._get_seller_store_id(user_id)

            if not ConversationService._verify_participant(conv, user_id, seller_store_id):
                return {'success': False, 'message': 'Bạn không có quyền thao tác trên cuộc trò chuyện này'}, 403

            utc = pytz.UTC
            now = datetime.now(utc)

            # Đánh dấu đã đọc tất cả tin nhắn của người khác chưa được đọc
            db.session.query(Message).filter(
                Message.conversation_id == conversation_id,
                Message.sender_user_id != user_id,
                Message.is_read == 0
            ).update({'is_read': 1, 'read_at': now, 'updated_at': now})

            db.session.commit()

            return {
                'success': True,
                'message': 'Đã đánh dấu đã đọc'
            }, 200

        except Exception as e:
            db.session.rollback()
            raise e

    # ── Private helper ────────────────────────────────────────────────────────
    @staticmethod
    def _conv_to_dict(conv):
        return {
            'conversation_id': conv.conversation_id,
            'customer_id': conv.customer_id,
            'store_id': conv.store_id,
            'order_id': conv.order_id,
            'status': conv.status,
            'last_message_at': conv.last_message_at.isoformat() if conv.last_message_at else None,
            'created_at': conv.created_at.isoformat() if conv.created_at else None,
            'updated_at': conv.updated_at.isoformat() if conv.updated_at else None,
        }
