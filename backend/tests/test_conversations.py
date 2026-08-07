"""Tests des conversations persistantes du chat.

Lancer : python tests/test_conversations.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app


def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "cv@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_create_append_and_reload():
    c, h = _auth()
    conv = c.post("/api/conversations", headers=h, json={}).get_json()
    cid = conv["id"]
    c.post(f"/api/conversations/{cid}/messages", headers=h,
           json={"role": "user", "content": "C'est quoi un transformer ?"})
    c.post(f"/api/conversations/{cid}/messages", headers=h,
           json={"role": "assistant", "content": "Un modèle d'attention.", "model": "qwen2.5:3b"})

    # Rechargement : les messages persistent + titre auto depuis le 1er message user.
    full = c.get(f"/api/conversations/{cid}", headers=h).get_json()
    assert len(full["messages"]) == 2
    assert full["messages"][0]["role"] == "user" and full["messages"][1]["model"] == "qwen2.5:3b"
    assert full["title"].startswith("C'est quoi un transformer")
    print(f"[persist]  conversation rechargée avec {len(full['messages'])} messages, titre auto")


def test_list_and_delete():
    c, h = _auth()
    a = c.post("/api/conversations", headers=h, json={"title": "A"}).get_json()
    c.post("/api/conversations", headers=h, json={"title": "B"})
    lst = c.get("/api/conversations", headers=h).get_json()["conversations"]
    assert len(lst) == 2
    c.delete(f"/api/conversations/{a['id']}", headers=h)
    assert len(c.get("/api/conversations", headers=h).get_json()["conversations"]) == 1
    print("[crud]     liste + suppression OK")


def test_isolation_between_users():
    c, h = _auth()
    cid = c.post("/api/conversations", headers=h, json={}).get_json()["id"]
    # Un autre utilisateur ne doit pas y accéder.
    r2 = c.post("/api/auth/register", json={"email": "other@u.sn", "password": "motdepasse123"})
    h2 = {"Authorization": f"Bearer {r2.get_json()['access_token']}"}
    assert c.get(f"/api/conversations/{cid}", headers=h2).status_code == 404
    print("[secu]     conversation d'un autre user -> 404")


if __name__ == "__main__":
    for t in [test_create_append_and_reload, test_list_and_delete, test_isolation_between_users]:
        t()
    print("\n✅ 3 tests conversations passés.")
