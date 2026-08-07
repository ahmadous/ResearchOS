"""Handlers SocketIO — connexion authentifiée par JWT + rooms par utilisateur.

Le client émet `join` avec son token ; on le vérifie et on l'ajoute à sa room
privée `user:<id>`. Aucune donnée n'est diffusée hors de cette room.
"""
from __future__ import annotations

import logging

from flask import current_app, request
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


def _stream_worker(app, sid, user_id, messages, strategy, pinned_model, use_memory):
    """Diffuse les tokens d'une complétion vers un client (thread de fond)."""
    with app.app_context():
        from ..services import LLMService
        try:
            chosen, tokens = LLMService().stream(
                user_id, messages, strategy=strategy, pinned_model=pinned_model,
                use_memory=use_memory)
            socketio.emit("chat_start", {"model": chosen.id, "provider": chosen.provider},
                          to=sid)
            for tok in tokens:
                socketio.emit("chat_token", {"text": tok}, to=sid)
            socketio.emit("chat_done", {"model": chosen.id}, to=sid)
        except Exception as e:  # noqa: BLE001
            socketio.emit("chat_error", {"message": str(e)}, to=sid)


@socketio.on("chat_stream")
def _on_chat_stream(data):
    data = data or {}
    user_id = _user_from_token(data.get("token", ""))
    if not user_id:
        emit("chat_error", {"message": "token invalide"})
        return
    app = current_app._get_current_object()
    socketio.start_background_task(
        _stream_worker, app, request.sid, user_id,
        data.get("messages", []), data.get("strategy", "balanced"),
        data.get("pinned_model"), data.get("use_memory", True))


def _agent_stream_worker(app, sid, user_id, agent, task, pinned_model):
    """Diffuse la sortie d'un agent token par token."""
    with app.app_context():
        from ..services import AgentService
        try:
            chosen, tokens = AgentService().stream(user_id, agent, task, pinned_model)
            socketio.emit("agent_start", {"agent": agent, "model": chosen.id}, to=sid)
            for tok in tokens:
                socketio.emit("agent_token", {"agent": agent, "text": tok}, to=sid)
            socketio.emit("agent_done", {"agent": agent, "model": chosen.id}, to=sid)
        except Exception as e:  # noqa: BLE001
            socketio.emit("agent_error", {"agent": agent, "message": str(e)}, to=sid)


@socketio.on("agent_stream")
def _on_agent_stream(data):
    data = data or {}
    user_id = _user_from_token(data.get("token", ""))
    if not user_id:
        emit("agent_error", {"message": "token invalide"})
        return
    app = current_app._get_current_object()
    socketio.start_background_task(
        _agent_stream_worker, app, request.sid, user_id,
        data.get("agent"), data.get("task", ""), data.get("pinned_model"))


def register_socketio_handlers() -> None:
    """Import déclenché depuis l'app factory pour enregistrer les handlers."""
    # Les décorateurs @socketio.on ci-dessus s'exécutent à l'import du module.
    return
