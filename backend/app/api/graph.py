"""Knowledge Graph API — visualiser, extraire (async), vider."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import KnowledgeGraphService, LLMServiceError, TaskService
from .schemas import GraphExtractSchema

blp = Blueprint("graph", __name__, url_prefix="/api/graph",
                description="Graphe de connaissances (entités & relations)")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Graph(MethodView):
    @jwt_required()
    def get(self):
        return KnowledgeGraphService().get_graph(_uid())

    @jwt_required()
    @blp.response(204)
    def delete(self):
        KnowledgeGraphService().clear(_uid())


@blp.route("/extract")
class Extract(MethodView):
    @jwt_required()
    @blp.arguments(GraphExtractSchema)
    def post(self, data):
        if not data.get("text") and not data.get("document_id"):
            abort(400, message="Fournir 'text' ou 'document_id'")
        params = {k: v for k, v in data.items() if v}
        try:
            return TaskService().enqueue(_uid(), "graph_extract", params), 202
        except LLMServiceError as e:
            abort(400, message=str(e))
