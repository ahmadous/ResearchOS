"""App factory — assemble l'application (DI par extensions.init_app).

Aucun état global : chaque appel produit une app indépendante (tests inclus).
"""
from __future__ import annotations

import os

from flask import Flask, jsonify

from .config import get_config
from .extensions import api, cors, db, jwt, socketio


def build_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    # --- Extensions ---
    db.init_app(app)
    jwt.init_app(app)
    # Origines autorisées : "*" en dev, restreintes en prod via CORS_ORIGINS
    # (liste séparée par des virgules, ex: "https://researchos.vercel.app").
    origins = app.config.get("CORS_ORIGINS", "*")
    cors.init_app(app, resources={r"/api/*": {"origins": origins}},
                  supports_credentials=False)
    api.init_app(app)
    socketio.init_app(app, cors_allowed_origins=origins)

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

    # --- Création auto des tables (idempotent) ---
    # create_all() ne crée que les tables MANQUANTes (ne modifie/supprime rien),
    # donc sûr à chaque démarrage. En attendant des migrations Alembic, cela suffit
    # pour provisionner une base neuve (ex: Supabase au premier déploiement).
    # Désactivable via AUTO_CREATE_TABLES=0 une fois les migrations en place.
    if os.getenv("AUTO_CREATE_TABLES", "1") != "0":
        with app.app_context():
            db.create_all()

    return app
