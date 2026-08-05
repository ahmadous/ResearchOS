"""Test d'intégration RAG via HTTP : ingestion -> liste -> requête citée.

Embeddings = hashing (hors-ligne, défaut). LLM = Ollama SIMULÉ (modèle présent +
complétion sans réseau). Lancer :  python tests/test_rag_api.py
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.ai.base import CompletionResponse, Usage
from app.ai.providers.ollama_provider import OllamaProvider

FAKE_INSTALLED = [{"name": "llama3.2:3b", "details": {"parameter_size": "3.2B"}}]

DOC = (
    "Les transformers reposent sur le mécanisme d'attention multi-têtes. "
    "L'attention permet au modèle de pondérer l'importance des mots entre eux. "
    "La photosynthèse, elle, concerne la conversion de lumière en énergie."
)


def _fake_complete(self, request):
    return CompletionResponse(
        content="D'après le contexte, l'attention pondère les mots [1].",
        model=request.model or "llama3.2:3b", provider="ollama",
        usage=Usage(prompt_tokens=20, completion_tokens=12), cost_usd=0.0, latency_ms=4.2)


@contextmanager
def fake_ollama():
    with patch.object(OllamaProvider, "_fetch_installed", return_value=FAKE_INSTALLED), \
         patch.object(OllamaProvider, "complete", _fake_complete):
        yield


def auth_client():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register",
               json={"email": "rag@univ.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_ingest_list_and_query():
    c, h = auth_client()

    r = c.post("/api/rag/documents", headers=h,
               json={"title": "Cours attention", "text": DOC})
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["n_chunks"] >= 1
    print(f"[ingest]   document indexé, {r.get_json()['n_chunks']} chunks")

    docs = c.get("/api/rag/documents", headers=h).get_json()["documents"]
    assert len(docs) == 1 and docs[0]["title"] == "Cours attention"
    print(f"[list]     {len(docs)} document listé")

    with fake_ollama():
        r = c.post("/api/rag/query", headers=h,
                   json={"question": "Que fait l'attention dans les transformers ?"})
    body = r.get_json()
    assert r.status_code == 200, body
    assert body["answer"] and body["references"]
    assert all(ref["document_id"] == docs[0]["id"] for ref in body["references"])
    print(f"[query]    réponse citée avec {len(body['references'])} référence(s)")


def test_query_without_documents():
    c, h = auth_client()
    with fake_ollama():
        r = c.post("/api/rag/query", headers=h, json={"question": "quoi ?"})
    assert r.status_code == 400 and "Aucun document" in r.get_json()["message"]
    print("[guard]    requête sans document -> 400 message clair")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests RAG (HTTP) passés.")
