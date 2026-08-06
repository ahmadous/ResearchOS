"""Exécution des tâches — abstraction avec repli local (Strategy).

- `InlineRunner` (défaut) : exécute le job dans un thread de fond via SocketIO
  (`start_background_task`). Zéro infrastructure requise.
- `SyncRunner` (tests) : exécute immédiatement, en synchrone, pour un test
  déterministe.
- `CeleryRunner` (optionnel, prod) : délègue à un worker Celery/Redis.

Comme pour les fournisseurs IA : l'infra lourde (Redis/Celery) est OPTIONNELLE.
"""
from __future__ import annotations

import abc
from typing import Callable

from flask import current_app

from ..extensions import socketio


class TaskRunner(abc.ABC):
    @abc.abstractmethod
    def submit(self, fn: Callable, *args) -> None: ...


class InlineRunner(TaskRunner):
    def submit(self, fn, *args):
        socketio.start_background_task(fn, *args)


class SyncRunner(TaskRunner):
    def submit(self, fn, *args):
        fn(*args)


class CeleryRunner(TaskRunner):
    """Optionnel : nécessite un broker Redis + worker en marche."""
    def submit(self, fn, *args):
        from .celery_app import dispatch
        dispatch(fn, *args)


def get_runner() -> TaskRunner:
    mode = current_app.config.get("TASK_RUNNER", "inline")
    return {"sync": SyncRunner, "celery": CeleryRunner}.get(mode, InlineRunner)()
