"""Instances d'extensions Flask, créées SANS app (pattern init_app).

Elles sont importées partout mais initialisées une seule fois dans `create_app`.
Ça évite les imports circulaires et permet plusieurs apps (tests) sans conflit.
"""
from __future__ import annotations

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
api = Api()
