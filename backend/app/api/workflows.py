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
        # Crée une exécution puis l'enfile ; la progression arrive par WebSocket.
        try:
            run = WorkflowService().create_run(_uid(), wf_id)
            task = TaskService().enqueue(_uid(), "workflow", {"run_id": run["id"]})
            return {"run": run, "task": task}, 202
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/runs")
class Runs(MethodView):
    @jwt_required()
    def get(self):
        return {"runs": WorkflowService().list_runs(_uid())}


@blp.route("/runs/<run_id>")
class RunItem(MethodView):
    @jwt_required()
    def get(self, run_id):
        try:
            return WorkflowService().get_run(_uid(), run_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/runs/<run_id>/pause")
class PauseRun(MethodView):
    @jwt_required()
    def post(self, run_id):
        try:
            return WorkflowService().pause_run(_uid(), run_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/runs/<run_id>/cancel")
class CancelRun(MethodView):
    @jwt_required()
    def post(self, run_id):
        try:
            return WorkflowService().cancel_run(_uid(), run_id)
        except LLMServiceError as e:
            abort(404, message=str(e))


@blp.route("/runs/<run_id>/resume")
class ResumeRun(MethodView):
    @jwt_required()
    def post(self, run_id):
        # Remet en 'running' et réenfile une tâche qui reprend là où on s'était arrêté.
        try:
            svc = WorkflowService()
            run = svc._run(_uid(), run_id)
            if run.status not in ("paused", "pending"):
                abort(409, message=f"Exécution non reprenable (statut: {run.status})")
            from ..extensions import db as _db
            run.status = "running"; _db.session.commit()
            task = TaskService().enqueue(_uid(), "workflow", {"run_id": run_id})
            return {"run": run.to_dict(), "task": task}, 202
        except LLMServiceError as e:
            abort(404, message=str(e))
