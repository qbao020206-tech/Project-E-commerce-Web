from flask import Blueprint
from controllers.conversation_controller import ConversationController
from middlewares.auth_middleware import token_required

conversation_bp = Blueprint('conversations', __name__, url_prefix='/api/v1')

# API 44: GET /api/v1/conversations — Customer, Seller
conversation_bp.add_url_rule(
    '/conversations',
    view_func=token_required(ConversationController.list_conversations),
    methods=['GET']
)

# API 45: POST /api/v1/conversations — Customer
conversation_bp.add_url_rule(
    '/conversations',
    view_func=token_required(ConversationController.create_conversation),
    methods=['POST']
)

# API 46: GET /api/v1/conversations/:id/messages — Customer, Seller
conversation_bp.add_url_rule(
    '/conversations/<int:conversation_id>/messages',
    view_func=token_required(ConversationController.get_messages),
    methods=['GET']
)

# API 47: POST /api/v1/conversations/:id/messages — Customer, Seller
conversation_bp.add_url_rule(
    '/conversations/<int:conversation_id>/messages',
    view_func=token_required(ConversationController.send_message),
    methods=['POST']
)

# API 48: PATCH /api/v1/conversations/:id/read — Customer, Seller
conversation_bp.add_url_rule(
    '/conversations/<int:conversation_id>/read',
    view_func=token_required(ConversationController.mark_as_read),
    methods=['PATCH']
)
