"""Instances d'extensions Flask, créées SANS app (pattern init_app).

Elles sont importées partout mais initialisées une seule fois dans `create_app`.
Ça évite les imports circulaires et permet plusieurs apps (tests) sans conflit.
"""
from __future__ import annotations

from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_smorest import Api
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()
api = Api()

# async_mode='threading' : pas besoin d'eventlet/gevent. Suffisant pour le dev
# et les tests ; en prod on peut passer un message_queue Redis pour scaler.
socketio = SocketIO(cors_allowed_origins="*", async_mode="threading")
