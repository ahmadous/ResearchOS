"""Tests WebSocket + tâches asynchrones — test client SocketIO, runner sync.

Aucun réseau, aucun Redis. Une SEULE app est partagée par le fichier (comme en
production où create_app n'est appelé qu'une fois : le singleton SocketIO ne doit
être init_app'd qu'une fois). Chaque test utilise un client + un user distincts.
Lancer :  python tests/test_realtime.py
"""
import sys
from itertools import count
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import socketio

APP = create_app("test")          # une seule app pour tout le fichier
_seq = count()


def _new_user():
    flask_client = APP.test_client()
    email = f"ws{next(_seq)}@univ.sn"
    r = flask_client.post("/api/auth/register",
                          json={"email": email, "password": "motdepasse123"})
    return flask_client, r.get_json()["access_token"]


def _names(received):
    return [m["name"] for m in received]


def test_join_requires_valid_token():
    flask_client, _ = _new_user()
    sio = socketio.test_client(APP, flask_test_client=flask_client)
    assert sio.is_connected()
    sio.emit("join", {"token": "invalide"})
    names = _names(sio.get_received())
    assert "join_error" in names and "joined" not in names
    sio.disconnect()
    print("[auth]     join avec token invalide -> join_error")


def test_join_ok_and_task_progress_events():
    flask_client, token = _new_user()
    sio = socketio.test_client(APP, flask_test_client=flask_client)
    sio.emit("join", {"token": token})
    assert "joined" in _names(sio.get_received())

    resp = flask_client.post("/api/tasks", headers={"Authorization": f"Bearer {token}"},
                             json={"kind": "rag_ingest",
                                   "params": {"title": "Doc", "text": "Un texte de test suffisant."}})
    assert resp.status_code == 202, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "completed"          # sync -> terminé au retour
    assert body["result"]["n_chunks"] >= 1

    events = _names(sio.get_received())
    assert "task_started" in events
    assert "task_progress" in events
    assert "task_completed" in events
    sio.disconnect()
    print(f"[ws]       événements reçus : {events}")


def test_task_status_endpoint():
    flask_client, token = _new_user()
    h = {"Authorization": f"Bearer {token}"}
    tid = flask_client.post("/api/tasks", headers=h,
                            json={"kind": "rag_ingest",
                                  "params": {"text": "contenu"}}).get_json()["id"]
    got = flask_client.get(f"/api/tasks/{tid}", headers=h).get_json()
    assert got["id"] == tid and got["status"] == "completed"
    lst = flask_client.get("/api/tasks", headers=h).get_json()["tasks"]
    assert any(t["id"] == tid for t in lst)
    print("[status]   GET /tasks/{id} et liste OK")


def test_invalid_job_marked_failed():
    flask_client, token = _new_user()
    r = flask_client.post("/api/tasks", headers={"Authorization": f"Bearer {token}"},
                          json={"kind": "rag_ingest", "params": {}})  # 'text' manquant
    assert r.status_code == 202
    assert r.get_json()["status"] == "failed"     # échec propre, pas de 500
    print("[robuste]  job invalide -> statut 'failed' (pas de crash)")


if __name__ == "__main__":
    # Ordre explicite (pas de tri) pour rester proche d'un usage réel.
    for t in [test_join_requires_valid_token, test_join_ok_and_task_progress_events,
              test_task_status_endpoint, test_invalid_job_marked_failed]:
        t()
    print("\n✅ 4 tests temps réel passés.")
