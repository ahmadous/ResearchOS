"""Chat API — complétion avec routage automatique (ou modèle épinglé)."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMService, LLMServiceError
from .schemas import ChatSchema

blp = Blueprint("chat", __name__, url_prefix="/api/chat",
                description="Complétion LLM routée")


@blp.route("/complete")
class Complete(MethodView):
    @jwt_required()
    @blp.arguments(ChatSchema)
    def post(self, data):
        try:
            return LLMService().complete(get_jwt_identity(), **data)
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec de la complétion: {e}")
