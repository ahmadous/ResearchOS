"""Évaluation API — fact-check et score de confiance d'une réponse."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import EvaluationService, LLMServiceError
from .schemas import EvaluateSchema

blp = Blueprint("evaluate", __name__, url_prefix="/api/evaluate",
                description="Évaluation critique des réponses (fiabilité)")


@blp.route("")
class Evaluate(MethodView):
    @jwt_required()
    @blp.arguments(EvaluateSchema)
    def post(self, data):
        try:
            return EvaluationService().evaluate(
                get_jwt_identity(), data["question"], data["answer"],
                data.get("context", ""), data.get("pinned_model"))
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec de l'évaluation: {e}")
