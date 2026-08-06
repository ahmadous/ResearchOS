"""Intégration HTTP : recherche scientifique (arXiv simulé) + import vers le RAG.

Réseau confiné : on patche `ArxivSource._fetch`. L'import utilise l'embedder
hashing (hors-ligne). Lancer :  python tests/test_scholar_api.py
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.scholar import ArxivSource
from tests.test_scholar import ARXIV_XML


@contextmanager
def fake_arxiv():
    with patch.object(ArxivSource, "_fetch", return_value=ARXIV_XML):
        yield


def auth_client():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register",
               json={"email": "sci@univ.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_search_arxiv():
    c, h = auth_client()
    with fake_arxiv():
        r = c.post("/api/scholar/search", headers=h,
                   json={"query": "transformers attention", "sources": ["arxiv"]})
    body = r.get_json()
    assert r.status_code == 200, body
    assert body["count"] == 1
    assert body["results"][0]["title"] == "Attention Is All You Need"
    print(f"[search]   arXiv -> {body['results'][0]['title']}")


def test_import_paper_into_rag():
    c, h = auth_client()
    paper = {"title": "Attention Is All You Need",
             "abstract": "Le mécanisme d'attention remplace la récurrence.",
             "authors": ["Ashish Vaswani"], "year": 2017,
             "doi": "10.5555/attn", "source": "arxiv"}
    r = c.post("/api/scholar/import", headers=h, json=paper)
    assert r.status_code == 201, r.get_json()
    assert r.get_json()["source_type"] == "paper"

    docs = c.get("/api/rag/documents", headers=h).get_json()["documents"]
    assert len(docs) == 1 and docs[0]["source_ref"] == "10.5555/attn"
    print(f"[import]   article -> Document RAG indexé ({docs[0]['n_chunks']} chunk(s))")


def test_sources_listed():
    c, h = auth_client()
    srcs = c.get("/api/scholar/sources", headers=h).get_json()["sources"]
    assert {"arxiv", "openalex", "semantic_scholar", "crossref", "hal"} <= set(srcs)
    print(f"[sources]  {len(srcs)} sources disponibles")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests scholar (HTTP) passés.")
