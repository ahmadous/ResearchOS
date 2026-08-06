"""Service de tâches asynchrones — crée la trace, soumet au runner, expose l'état."""
from __future__ import annotations

from flask import current_app

from ..extensions import db
from ..models import Task
from ..models.task import PENDING
from ..repositories import TaskRepository
from ..tasks.jobs import WORK, run_job
from ..tasks.runner import get_runner
from .llm_service import LLMServiceError


class TaskService:
    def __init__(self, tasks: TaskRepository | None = None):
        self.tasks = tasks or TaskRepository()

    def enqueue(self, user_id: str, kind: str, params: dict) -> dict:
        if kind not in WORK:
            raise LLMServiceError(f"Type de tâche inconnu: {kind} (dispo: {list(WORK)})")
        task = Task(user_id=user_id, kind=kind, status=PENDING)
        self.tasks.add(task)
        # L'app réelle est passée au job pour qu'il ouvre son propre contexte.
        app = current_app._get_current_object()
        get_runner().submit(run_job, app, task.id, user_id, kind, params)
        # Le runner sync met à jour la tâche dans une autre session : on expire le
        # cache pour renvoyer l'état réel (inline/async : reste 'pending', normal).
        db.session.expire_all()
        return self.tasks.get(task.id).to_dict()

    def get(self, user_id: str, task_id: str) -> dict:
        task = self.tasks.get(task_id)
        if not task or task.user_id != user_id:
            raise LLMServiceError("Tâche introuvable")
        return task.to_dict()

    def list(self, user_id: str) -> list[dict]:
        return [t.to_dict() for t in self.tasks.for_user(user_id)]
