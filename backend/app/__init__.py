"""Package applicatif ResearchOS.

`create_app` importe l'app factory de façon paresseuse : importer `app.ai`
(couche IA pure) ne charge donc jamais Flask. Utilisation :
    flask --app app:create_app run
"""
from __future__ import annotations


def create_app(config_name: str | None = None):
    from .app_factory import build_app
    return build_app(config_name)

