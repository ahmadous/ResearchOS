"""Package applicatif ResearchOS.

`create_app` importe l'app factory de façon paresseuse : importer `app.ai`
(couche IA pure) ne charge donc jamais Flask. Utilisation :
    flask --app app:create_app run
"""
from __future__ import annotations


def create_app(config_name: str | None = None):
    import os
    from .app_factory import build_app
    # Priorité : argument explicite, sinon variable d'env FLASK_CONFIG
    # (ex: "prod" sur Render), sinon DevConfig par défaut.
    return build_app(config_name or os.getenv("FLASK_CONFIG"))

