"""Configuration par environnement.

Un objet de config par environnement (dev/test/prod). `create_app` en choisit un
via la variable d'env `FLASK_CONFIG`. Aucune valeur secrète en dur : tout vient
de l'environnement, avec des défauts sûrs pour le dev.
"""
from __future__ import annotations

import os
from datetime import timedelta


class BaseConfig:
    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    JSON_SORT_KEYS = False

    # --- SQLAlchemy ---
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///researchos.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- JWT ---
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # --- Chiffrement des clés API stockées (Fernet). 32 octets base64url. ---
    # En prod, fournir CREDENTIAL_KEY. En dev on en dérive une par défaut.
    CREDENTIAL_KEY = os.getenv("CREDENTIAL_KEY")

    # --- OpenAPI / Swagger (flask-smorest) ---
    API_TITLE = "ResearchOS API"
    API_VERSION = "v1"
    OPENAPI_VERSION = "3.0.3"
    OPENAPI_URL_PREFIX = "/"
    OPENAPI_SWAGGER_UI_PATH = "/docs"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    API_SPEC_OPTIONS = {
        "security": [{"bearerAuth": []}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            }
        },
    }

    # --- Redis / Celery (Phase 6) ---
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # Exécution des tâches : "inline" (thread local, défaut), "celery" (prod), "sync" (tests).
    TASK_RUNNER = os.getenv("TASK_RUNNER", "inline")

    # --- Ollama (socle local, toujours disponible en fallback) ---
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
    # Durée de maintien du modèle en mémoire (évite le rechargement). Ex: "30m", "-1" (toujours).
    OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")

    # --- Rapports (PDF générés) ---
    REPORTS_DIR = os.getenv("REPORTS_DIR",
                            os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                         "generated_reports"))

    # --- RAG / Embeddings ---
    # "hashing" (déterministe, hors-ligne, défaut) ou "ollama" (nomic-embed-text).
    EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "hashing")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")


class DevConfig(BaseConfig):
    DEBUG = True


class TestConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    TASK_RUNNER = "sync"   # jobs exécutés en synchrone -> tests déterministes


class ProdConfig(BaseConfig):
    DEBUG = False

    def __init__(self):
        # En prod, les secrets DOIVENT venir de l'environnement.
        for var in ("SECRET_KEY", "JWT_SECRET_KEY", "CREDENTIAL_KEY", "DATABASE_URL"):
            if not os.getenv(var):
                raise RuntimeError(f"Variable d'environnement requise en prod: {var}")


CONFIGS = {"dev": DevConfig, "test": TestConfig, "prod": ProdConfig}


def get_config(name: str | None = None):
    name = name or os.getenv("FLASK_CONFIG", "dev")
    cfg = CONFIGS.get(name, DevConfig)
    return cfg() if isinstance(cfg, type) and name == "prod" else cfg
