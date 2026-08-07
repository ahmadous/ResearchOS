"""Tests du Memory Engine — rappel sémantique + HTTP + injection dans le chat.

Embeddings hashing (hors-ligne). Lancer : python tests/test_memory.py
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.ai.base import CompletionResponse, Usage
from app.ai.providers.ollama_provider import OllamaProvider


def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "mem@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_remember_list_and_delete():
    c, h = _auth()
    m1 = c.post("/api/memory", headers=h, json={"content": "L'utilisateur préfère Python à Java."}).get_json()
    c.post("/api/memory", headers=h, json={"content": "Le projet cible les inondations au Sénégal.", "scope": "project", "project": "flood"})
    all_mem = c.get("/api/memory", headers=h).get_json()["memories"]
    assert len(all_mem) == 2
    proj = c.get("/api/memory?scope=project", headers=h).get_json()["memories"]
    assert len(proj) == 1 and proj[0]["project"] == "flood"
    c.delete(f"/api/memory/{m1['id']}", headers=h)
    assert len(c.get("/api/memory", headers=h).get_json()["memories"]) == 1
    print("[crud]     mémoriser / lister (par portée) / supprimer OK")


def test_recall_is_semantic():
    c, h = _auth()
    c.post("/api/memory", headers=h, json={"content": "Les transformers utilisent le mécanisme d'attention."})
    c.post("/api/memory", headers=h, json={"content": "La photosynthèse convertit la lumière en énergie."})
    r = c.post("/api/memory/recall", headers=h, json={"query": "comment marche l'attention des transformers ?"})
    hits = r.get_json()["results"]
    assert hits and "attention" in hits[0]["content"].lower()
    print(f"[recall]   top: '{hits[0]['content'][:40]}…' (score {hits[0]['score']})")


# --- Injection dans le chat ---
CAPTURED = {}


def _fake_complete(self, request):
    return CompletionResponse(content="ok", model="x", provider="ollama",
                              usage=Usage(1, 1))


def _fake_stream(self, request):
    CAPTURED["messages"] = [(m.role, m.content) for m in request.messages]
    return iter(["ok"])


@contextmanager
def fake_ollama():
    with patch.object(OllamaProvider, "_fetch_installed",
                      return_value=[{"name": "llama3.2:1b", "details": {"parameter_size": "1.2B"}}]), \
         patch.object(OllamaProvider, "complete", _fake_complete), \
         patch.object(OllamaProvider, "stream", _fake_stream):
        yield


def test_memory_injected_into_chat_stream():
    from flask_jwt_extended import decode_token
    from app.services import LLMService
    app = create_app("test")
    fc = app.test_client()
    token = fc.post("/api/auth/register", json={"email": "mc@u.sn", "password": "motdepasse123"}).get_json()["access_token"]
    fc.post("/api/memory", headers={"Authorization": f"Bearer {token}"},
            json={"content": "L'utilisateur s'appelle Ahmadou et étudie les inondations."})
    with app.app_context():
        uid = decode_token(token)["sub"]
        with fake_ollama():
            chosen, tokens = LLMService().stream(
                uid, [{"role": "user", "content": "Rappelle-moi sur quoi je travaille (inondations) ?"}],
                pinned_model="llama3.2:1b", use_memory=True)
            list(tokens)   # consomme -> déclenche stream -> capture les messages
    system_texts = " ".join(c for r, c in CAPTURED["messages"] if r == "system")
    assert "Ahmadou" in system_texts and "inondations" in system_texts
    print("[chat]     la mémoire pertinente est injectée dans le prompt système")


def test_memory_off_not_injected():
    from flask_jwt_extended import decode_token
    from app.services import LLMService
    app = create_app("test")
    fc = app.test_client()
    token = fc.post("/api/auth/register", json={"email": "mc2@u.sn", "password": "motdepasse123"}).get_json()["access_token"]
    fc.post("/api/memory", headers={"Authorization": f"Bearer {token}"}, json={"content": "Secret: 42."})
    CAPTURED.clear()
    with app.app_context():
        uid = decode_token(token)["sub"]
        with fake_ollama():
            _, tokens = LLMService().stream(uid, [{"role": "user", "content": "coucou"}],
                                            pinned_model="llama3.2:1b", use_memory=False)
            list(tokens)
    system_texts = " ".join(c for r, c in CAPTURED["messages"] if r == "system")
    assert "Secret" not in system_texts
    print("[chat]     use_memory=False -> aucune mémoire injectée")


if __name__ == "__main__":
    for t in [test_remember_list_and_delete, test_recall_is_semantic,
              test_memory_injected_into_chat_stream, test_memory_off_not_injected]:
        t()
    print("\n✅ 4 tests memory passés.")
