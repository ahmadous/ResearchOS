"""Workflows API — CRUD + exécution (asynchrone, progression par nœud via WS)."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, TaskService, WorkflowService
from .schemas import WorkflowSchema

blp = Blueprint("workflows", __name__, url_prefix="/api/workflows",
                description="Constructeur de workflows d'agents (drag & drop)")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Workflows(MethodView):
    @jwt_required()
    def get(self):
        return {"workflows": WorkflowService().list(_uid())}

    @jwt_required()
    @blp.arguments(WorkflowSchema)
    def post(self, data):
        return WorkflowService().create(_uid(), data.get("name"), data.get("graph")), 201


@blp.route("/<wf_id>")
class WorkflowItem(MethodView):
    @jwt_required()
    def get(self, wf_id):
        try:
            return WorkflowService().get(_uid(), wf_id).to_dict()
        except LLMServiceError as e:
            abort(404, message=str(e))

    @jwt_required()
    @blp.arguments(WorkflowSchema)
    def put(self, data, wf_id):
        try:
            return WorkflowService().update(_uid(), wf_id, name=data.get("name"),
                                            graph=data.get("graph"))
        except LLMServiceError as e:
            abort(404, message=str(e))

    @jwt_required()
    @blp.response(204)
    def delete(self, wf_id):
        try:
            WorkflowService().delete(_uid(), wf_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/<wf_id>/run")
class RunWorkflow(MethodView):
    @jwt_required()
    def post(self, wf_id):
        # Lancé comme tâche asynchrone : la progression arrive par WebSocket.
        try:
            return TaskService().enqueue(_uid(), "workflow", {"workflow_id": wf_id}), 202
        except LLMServiceError as e:
            abort(400, message=str(e))
