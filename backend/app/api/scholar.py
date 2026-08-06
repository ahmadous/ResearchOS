"""Recherche scientifique API — multi-sources + import vers le RAG."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, ScholarService
from .schemas import ScholarImportSchema, ScholarSearchSchema

blp = Blueprint("scholar", __name__, url_prefix="/api/scholar",
                description="Recherche scientifique (arXiv, OpenAlex, Semantic Scholar…)")


@blp.route("/sources")
class Sources(MethodView):
    @jwt_required()
    def get(self):
        return {"sources": ScholarService().available_sources()}


@blp.route("/search")
class Search(MethodView):
    @jwt_required()
    @blp.arguments(ScholarSearchSchema)
    def post(self, data):
        try:
            return ScholarService().search(
                data["query"], data.get("sources"), data["limit"])
        except Exception as e:
            abort(502, message=f"Échec de la recherche: {e}")


@blp.route("/import")
class Import(MethodView):
    @jwt_required()
    @blp.arguments(ScholarImportSchema)
    def post(self, data):
        try:
            return ScholarService().import_paper(get_jwt_identity(), data), 201
        except LLMServiceError as e:
            abort(400, message=str(e))
