"""Conversations API — persistance du chat."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import ConversationService, LLMServiceError
from .schemas import ConversationCreateSchema, MessageAppendSchema

blp = Blueprint("conversations", __name__, url_prefix="/api/conversations",
                description="Conversations de chat persistantes")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Conversations(MethodView):
    @jwt_required()
    def get(self):
        return {"conversations": ConversationService().list(_uid())}

    @jwt_required()
    @blp.arguments(ConversationCreateSchema)
    def post(self, data):
        return ConversationService().create(_uid(), data.get("title")), 201


@blp.route("/<conv_id>")
class ConversationItem(MethodView):
    @jwt_required()
    def get(self, conv_id):
        try:
            return ConversationService().get(_uid(), conv_id)
        except LLMServiceError as e:
            abort(404, message=str(e))

    @jwt_required()
    @blp.response(204)
    def delete(self, conv_id):
        try:
            ConversationService().delete(_uid(), conv_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/<conv_id>/messages")
class Messages(MethodView):
    @jwt_required()
    @blp.arguments(MessageAppendSchema)
    def post(self, data, conv_id):
        try:
            return ConversationService().append(
                _uid(), conv_id, data["role"], data["content"], data.get("model"))
        except LLMServiceError as e:
            abort(404, message=str(e))
