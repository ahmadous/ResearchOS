"""Agents API — lister, exécuter un agent, chaîner (pipeline), mode auto."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import AgentService, LLMServiceError
from .schemas import AgentAutoSchema, AgentPipelineSchema, AgentRunSchema

blp = Blueprint("agents", __name__, url_prefix="/api/agents",
                description="Agents IA spécialisés et orchestration")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Agents(MethodView):
    @jwt_required()
    def get(self):
        return {"agents": AgentService().list_agents(_uid())}


@blp.route("/<name>/run")
class RunAgent(MethodView):
    @jwt_required()
    @blp.arguments(AgentRunSchema)
    def post(self, data, name):
        try:
            return AgentService().run(_uid(), name, data["task"], data.get("goal"))
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec de l'agent: {e}")


@blp.route("/pipeline")
class Pipeline(MethodView):
    @jwt_required()
    @blp.arguments(AgentPipelineSchema)
    def post(self, data):
        try:
            return AgentService().pipeline(_uid(), data["steps"], data["goal"])
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec du pipeline: {e}")


@blp.route("/auto")
class Auto(MethodView):
    @jwt_required()
    @blp.arguments(AgentAutoSchema)
    def post(self, data):
        try:
            return AgentService().auto(_uid(), data["goal"], data["max_steps"])
        except LLMServiceError as e:
            abort(400, message=str(e))
        except Exception as e:
            abort(502, message=f"Échec de l'orchestration: {e}")
