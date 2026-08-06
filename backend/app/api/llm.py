"""LLM Manager API — ajouter provider, tester modèle, coûts/latence/tokens, conso."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMService, LLMServiceError
from .schemas import ProviderCreateSchema, ProviderSchema, TestModelSchema

blp = Blueprint("llm", __name__, url_prefix="/api/llm",
                description="Gestion des modèles et fournisseurs IA")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("/providers/available")
class AvailableProviders(MethodView):
    @jwt_required()
    def get(self):
        return {"providers": LLMService().available_providers()}


@blp.route("/ollama")
class OllamaStatus(MethodView):
    @jwt_required()
    def get(self):
        """État du démon Ollama local + modèles installés sur la machine."""
        return LLMService().ollama_status(_uid())


@blp.route("/providers")
class Providers(MethodView):
    @jwt_required()
    @blp.response(200, ProviderSchema(many=True))
    def get(self):
        return LLMService().list_providers(_uid())

    @jwt_required()
    @blp.arguments(ProviderCreateSchema)
    @blp.response(201, ProviderSchema)
    def post(self, data):
        try:
            return LLMService().add_provider(_uid(), **data)
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/providers/<cred_id>")
class Provider(MethodView):
    @jwt_required()
    @blp.response(204)
    def delete(self, cred_id):
        try:
            LLMService().delete_provider(_uid(), cred_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/models")
class Models(MethodView):
    @jwt_required()
    def get(self):
        return {"models": LLMService().catalog(_uid())}


@blp.route("/test")
class TestModel(MethodView):
    @jwt_required()
    @blp.arguments(TestModelSchema)
    def post(self, data):
        try:
            return LLMService().test_model(_uid(), data["model"])
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:  # erreur réseau/provider -> réponse propre
            abort(502, message=f"Échec du test: {e}")


@blp.route("/consumption")
class Consumption(MethodView):
    @jwt_required()
    def get(self):
        return LLMService().consumption(_uid())


@blp.route("/routing/preview")
class RoutingPreview(MethodView):
    @jwt_required()
    def get(self):
        from flask import request
        strategy = request.args.get("strategy", "balanced")
        privacy = request.args.get("require_privacy")
        try:
            return {"ranking": LLMService().preview_routing(_uid(), strategy, privacy)}
        except LLMServiceError as e:
            abort(400, message=str(e))
