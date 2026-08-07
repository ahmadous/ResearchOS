"""Memory Engine API — mémoriser, lister, rappeler (sémantique), supprimer."""
from __future__ import annotations

from flask import request
from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, MemoryService
from .schemas import MemoryCreateSchema, MemoryRecallSchema

blp = Blueprint("memory", __name__, url_prefix="/api/memory",
                description="Mémoire persistante (rappel sémantique entre sessions)")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Memory(MethodView):
    @jwt_required()
    def get(self):
        return {"memories": MemoryService().list(
            _uid(), scope=request.args.get("scope"),
            project=request.args.get("project"))}

    @jwt_required()
    @blp.arguments(MemoryCreateSchema)
    def post(self, data):
        try:
            return MemoryService().remember(_uid(), **data), 201
        except LLMServiceError as e:
            abort(400, message=str(e))

    @jwt_required()
    @blp.response(200)
    def delete(self):
        n = MemoryService().clear(_uid(), scope=request.args.get("scope"))
        return {"cleared": n}


@blp.route("/<item_id>")
class MemoryItemView(MethodView):
    @jwt_required()
    @blp.response(204)
    def delete(self, item_id):
        try:
            MemoryService().delete(_uid(), item_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/recall")
class Recall(MethodView):
    @jwt_required()
    @blp.arguments(MemoryRecallSchema)
    def post(self, data):
        return {"results": MemoryService().recall(
            _uid(), data["query"], k=data["k"],
            scope=data.get("scope"), project=data.get("project"))}
