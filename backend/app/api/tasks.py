"""Tasks API — lancer un job asynchrone et suivre sa progression (WebSocket)."""
from __future__ import annotations

from flask.views import MethodView
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_smorest import Blueprint, abort

from ..services import LLMServiceError, TaskService
from .schemas import TaskCreateSchema

blp = Blueprint("tasks", __name__, url_prefix="/api/tasks",
                description="Tâches asynchrones + progression temps réel")


def _uid() -> str:
    return get_jwt_identity()


@blp.route("")
class Tasks(MethodView):
    @jwt_required()
    def get(self):
        return {"tasks": TaskService().list(_uid())}

    @jwt_required()
    @blp.arguments(TaskCreateSchema)
    def post(self, data):
        try:
            return TaskService().enqueue(_uid(), data["kind"], data["params"]), 202
        except LLMServiceError as e:
            abort(400, message=str(e))


@blp.route("/<task_id>")
class TaskItem(MethodView):
    @jwt_required()
    def get(self, task_id):
        try:
            return TaskService().get(_uid(), task_id)
        except LLMServiceError as e:
            abort(404, message=str(e))
