"""Notifier temps réel (Observer) — émet des événements vers la room d'un user.

Chaque utilisateur rejoint une room `user:<id>` à la connexion WebSocket. Les
jobs longs poussent leur progression ici ; le front s'abonne et met à jour l'UI.
"""
from __future__ import annotations

from ..extensions import socketio


def _room(user_id: str) -> str:
    return f"user:{user_id}"


def emit_to_user(user_id: str, event: str, payload: dict) -> None:
    socketio.emit(event, payload, room=_room(user_id))


def task_started(user_id: str, task_id: str, kind: str) -> None:
    emit_to_user(user_id, "task_started",
                 {"task_id": task_id, "kind": kind, "status": "running", "progress": 0})


def task_progress(user_id: str, task_id: str, progress: int, message: str = "") -> None:
    emit_to_user(user_id, "task_progress",
                 {"task_id": task_id, "progress": progress, "message": message})


def task_completed(user_id: str, task_id: str, result: dict | None = None) -> None:
    emit_to_user(user_id, "task_completed",
                 {"task_id": task_id, "status": "completed", "progress": 100,
                  "result": result})


def task_failed(user_id: str, task_id: str, error: str) -> None:
    emit_to_user(user_id, "task_failed",
                 {"task_id": task_id, "status": "failed", "error": error})


def notify(user_id: str, title: str, level: str = "info") -> None:
    """Notification générique (toast côté client)."""
    emit_to_user(user_id, "notification", {"title": title, "level": level})


def workflow_node(user_id: str, task_id: str, node_id: str, status: str,
                  output: str | None = None) -> None:
    """Mise à jour de l'état d'un nœud pendant l'exécution d'un workflow."""
    emit_to_user(user_id, "workflow_node",
                 {"task_id": task_id, "node_id": node_id, "status": status,
                  "output": (output[:400] if output else None)})
