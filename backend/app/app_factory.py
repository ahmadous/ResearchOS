"""App factory — assemble l'application (DI par extensions.init_app).

Aucun état global : chaque appel produit une app indépendante (tests inclus).
"""
from __future__ import annotations

from flask import Flask, jsonify

from .config import get_config
from .extensions import api, cors, db, jwt, socketio


def build_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # --- Extensions ---
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    api.init_app(app)
    socketio.init_app(app)

    # --- Modèles (enregistre les tables) + blueprints ---
    from . import models  # noqa: F401
    from .api import register_blueprints
    register_blueprints()

    # --- Handlers WebSocket (enregistrés à l'import du module) ---
    from .realtime import register_socketio_handlers
    register_socketio_handlers()

    # --- JWT: réponses d'erreur propres ---
    @jwt.expired_token_loader
    def _expired(_h, _p):
        return jsonify(message="Token expiré"), 401

    @jwt.unauthorized_loader
    def _missing(_reason):
        return jsonify(message="Token manquant"), 401

    # --- Healthcheck ---
    @app.get("/health")
    def health():
        return {"status": "ok", "service": "researchos-backend"}

    # --- Création auto des tables en dev (prod: migrations Alembic) ---
    if app.config.get("DEBUG") or app.config.get("TESTING"):
        with app.app_context():
            db.create_all()

    return app
