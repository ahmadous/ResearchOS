"""Enregistrement des blueprints API sur l'objet flask-smorest `Api`."""
from __future__ import annotations

from ..extensions import api
from .agents import blp as agents_blp
from .auth import blp as auth_blp
from .chat import blp as chat_blp
from .conversations import blp as conversations_blp
from .evaluate import blp as evaluate_blp
from .graph import blp as graph_blp
from .llm import blp as llm_blp
from .memory import blp as memory_blp
from .reports import blp as reports_blp
from .rag import blp as rag_blp
from .scholar import blp as scholar_blp
from .tasks import blp as tasks_blp
from .workflows import blp as workflows_blp


def register_blueprints() -> None:
    api.register_blueprint(auth_blp)
    api.register_blueprint(llm_blp)
    api.register_blueprint(chat_blp)
    api.register_blueprint(agents_blp)
    api.register_blueprint(rag_blp)
    api.register_blueprint(scholar_blp)
    api.register_blueprint(tasks_blp)
    api.register_blueprint(workflows_blp)
    api.register_blueprint(graph_blp)
    api.register_blueprint(evaluate_blp)
    api.register_blueprint(memory_blp)
    api.register_blueprint(reports_blp)
    api.register_blueprint(conversations_blp)
