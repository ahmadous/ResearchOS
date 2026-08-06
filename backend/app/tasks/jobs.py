"""Jobs asynchrones : agent, ingestion RAG, import d'article.

Chaque job rapporte sa progression via un callback `progress(pct, msg)` qui
met à jour la tâche en base ET émet un événement WebSocket (notifier).
"""
from __future__ import annotations

from ..models.task import COMPLETED, FAILED, RUNNING
from ..realtime import notifier
from ..repositories import TaskRepository


# --- Fonctions de travail (work) : (progress, user_id, params) -> result ---
def _agent_work(progress, user_id, params):
    from ..services import AgentService
    progress(15, "routage du modèle…")
    result = AgentService().run(user_id, params["agent"], params["task"], params.get("goal"))
    progress(90, "finalisation…")
    return result


def _rag_ingest_work(progress, user_id, params):
    from ..services import RAGService
    progress(20, "découpage & embeddings…")
    doc = RAGService().ingest_text(
        user_id, title=params.get("title", "Sans titre"), text=params["text"],
        source_type=params.get("source_type", "text"))
    progress(90, "indexation…")
    return doc


def _scholar_import_work(progress, user_id, params):
    from ..services import ScholarService
    progress(30, "récupération de l'article…")
    return ScholarService().import_paper(user_id, params["paper"])


def _workflow_work(progress, user_id, params):
    from ..services import WorkflowService
    progress(5, "planification du graphe…")
    return WorkflowService().execute(
        user_id, params["workflow_id"], params["_task_id"],
        progress=progress, inputs=params.get("inputs"))


WORK = {
    "agent": _agent_work,
    "rag_ingest": _rag_ingest_work,
    "scholar_import": _scholar_import_work,
    "workflow": _workflow_work,
}


def run_job(app, task_id: str, user_id: str, kind: str, params: dict) -> None:
    """Exécute un job dans son propre contexte applicatif, avec suivi + WS."""
    with app.app_context():
        repo = TaskRepository()
        task = repo.get(task_id)
        if not task:
            return
        task.status = RUNNING
        repo.commit()
        notifier.task_started(user_id, task_id, kind)

        def progress(pct: int, message: str = ""):
            task.progress = int(pct)
            task.message = message
            repo.commit()
            notifier.task_progress(user_id, task_id, int(pct), message)

        try:
            work = WORK[kind]
            # Certains jobs (workflow) ont besoin de l'id de tâche pour émettre
            # des événements ciblés : on l'injecte dans les params.
            result = work(progress, user_id, {**params, "_task_id": task_id})
            task.status = COMPLETED
            task.progress = 100
            task.result = result
            repo.commit()
            notifier.task_completed(user_id, task_id, result)
        except Exception as e:  # noqa: BLE001 — on veut capturer tout échec
            task.status = FAILED
            task.error = str(e)
            repo.commit()
            notifier.task_failed(user_id, task_id, str(e))
