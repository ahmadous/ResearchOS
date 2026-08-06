"""Enregistrement des blueprints API sur l'objet flask-smorest `Api`."""
from __future__ import annotations

from ..extensions import api
from .agents import blp as agents_blp
from .auth import blp as auth_blp
from .chat import blp as chat_blp
from .llm import blp as llm_blp
from .rag import blp as rag_blp
from .scholar import blp as scholar_blp


def register_blueprints() -> None:
    api.register_blueprint(auth_blp)
    api.register_blueprint(llm_blp)
    api.register_blueprint(chat_blp)
    api.register_blueprint(agents_blp)
    api.register_blueprint(rag_blp)
    api.register_blueprint(scholar_blp)
