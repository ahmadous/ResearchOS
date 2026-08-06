"""Handlers SocketIO — connexion authentifiée par JWT + rooms par utilisateur.

Le client émet `join` avec son token ; on le vérifie et on l'ajoute à sa room
privée `user:<id>`. Aucune donnée n'est diffusée hors de cette room.
"""
from __future__ import annotations

import logging

from flask_jwt_extended import decode_token
from flask_socketio import emit, join_room

from ..extensions import socketio

log = logging.getLogger("researchos.ws")


def _user_from_token(token: str) -> str | None:
    try:
        return decode_token(token)["sub"]   # identity JWT
    except Exception:
        return None


@socketio.on("connect")
def _on_connect():
    # Connexion acceptée ; l'authentification se fait via l'événement `join`.
    emit("connected", {"ok": True})


@socketio.on("join")
def _on_join(data):
    token = (data or {}).get("token", "")
    user_id = _user_from_token(token)
    if not user_id:
        emit("join_error", {"message": "token invalide"})
        return
    join_room(f"user:{user_id}")
    emit("joined", {"room": f"user:{user_id}"})


@socketio.on("disconnect")
def _on_disconnect():
    log.debug("client déconnecté")


def register_socketio_handlers() -> None:
    """Import déclenché depuis l'app factory pour enregistrer les handlers."""
    # Les décorateurs @socketio.on ci-dessus s'exécutent à l'import du module.
    return
