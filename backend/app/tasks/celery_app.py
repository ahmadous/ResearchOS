"""Intégration Celery — OPTIONNELLE (montée en charge en production).

Activée seulement si `TASK_RUNNER=celery` et qu'un worker + Redis tournent.
Par défaut la plateforme utilise l'InlineRunner (aucune infra requise).

Lancer un worker :
    celery -A app.tasks.celery_app:get_celery worker --loglevel=info
"""
from __future__ import annotations

_celery = None


def get_celery():
    global _celery
    if _celery is not None:
        return _celery

    from celery import Celery
    from flask import current_app

    broker = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
    _celery = Celery("researchos", broker=broker, backend=broker)

    @_celery.task(name="researchos.run_task")
    def _run(task_id, user_id, kind, params):  # exécuté côté worker
        from .. import create_app
        from .jobs import run_job
        app = create_app()
        run_job(app, task_id, user_id, kind, params)

    _celery.run_task = _run
    return _celery


def dispatch(fn, app, task_id, user_id, kind, params):
    """Signature alignée sur runner.submit(run_job, app, task_id, user_id, kind, params)."""
    get_celery().run_task.delay(task_id, user_id, kind, params)
