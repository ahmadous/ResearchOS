"""Tests Revue de littérature — recherche sync immédiate, BibTeX, PDF, synthèse option.

Lancer : python tests/test_reports.py
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.ai.base import CompletionResponse, Usage
from app.ai.providers.ollama_provider import OllamaProvider
from app.reports import render_digest_pdf, to_bibtex
from app.services.scholar_service import ScholarService

FAKE = {
    "count": 2, "errors": {},
    "results": [
        {"title": "Flood mapping with deep learning", "authors": ["Awa Diop", "B. Sow"],
         "year": 2023, "url": "https://arxiv.org/abs/1", "source": "arxiv", "venue": "CVPR",
         "citations": 42, "doi": "10.1/x",
         "abstract": "We propose a CNN for flood mapping from satellite imagery."},
        {"title": "Sentinel-1 SAR flood detection", "authors": ["C. Ndiaye"],
         "year": 2022, "url": "https://openalex.org/W2", "source": "openalex",
         "citations": 7, "abstract": "SAR-based flood detection over West Africa."},
    ],
}


def test_bibtex_from_real_data():
    bib = to_bibtex(FAKE["results"])
    assert "@article{diop2023" in bib and "author = {Awa Diop and B. Sow}" in bib
    print("[bibtex]   entrées générées depuis les métadonnées réelles")


def test_render_digest_pdf():
    pdf = render_digest_pdf("flood mapping", FAKE["results"])
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1500
    print(f"[pdf]      digest (tableau+résumés) généré ({len(pdf)} octets)")


def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "rep@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_search_is_immediate_and_llm_free():
    c, h = _auth()
    def _boom(self, req):
        raise AssertionError("la RECHERCHE ne doit JAMAIS appeler le LLM")
    with patch.object(ScholarService, "search", return_value=FAKE), \
         patch.object(OllamaProvider, "complete", _boom):
        r = c.post("/api/reports/search", headers=h, json={"query": "flood mapping satellite"})
    body = r.get_json()
    assert r.status_code == 200 and body["count"] == 2 and "synthesis" not in body
    assert body["results"][0]["abstract"] and body["results"][0]["citations"] == 42
    assert body["results"][0]["url"] and "@article" in body["bibtex"]
    print(f"[search]   {body['count']} articles + BibTeX, SANS appel LLM (jamais de 500)")


def _fake_complete(self, req):
    return CompletionResponse(content="- CNN commun [1].\n- SAR différent [2].",
                              model=req.model or "llama3.2:1b", provider="ollama", usage=Usage(50, 40))


@contextmanager
def fake_llm():
    with patch.object(OllamaProvider, "_fetch_installed",
                      return_value=[{"name": "llama3.2:1b", "details": {"parameter_size": "1.2B"}}]), \
         patch.object(OllamaProvider, "complete", _fake_complete):
        yield


def test_synthesize_is_separate_endpoint():
    c, h = _auth()
    with fake_llm():
        r = c.post("/api/reports/synthesize", headers=h,
                   json={"query": "flood mapping", "papers": FAKE["results"]})
    assert r.status_code == 200 and r.get_json()["synthesis"].startswith("- CNN")
    print("[synth]    synthèse via endpoint séparé (n'affecte pas la recherche)")


def test_pdf_export_from_results():
    c, h = _auth()
    r = c.post("/api/reports/pdf", headers=h,
               json={"query": "flood mapping", "papers": FAKE["results"]})
    assert r.status_code == 200 and r.data[:5] == b"%PDF-"
    assert r.headers["Content-Type"] == "application/pdf"
    print(f"[export]   PDF rendu depuis les résultats ({len(r.data)} octets)")


if __name__ == "__main__":
    for t in [test_bibtex_from_real_data, test_render_digest_pdf,
              test_search_is_immediate_and_llm_free, test_synthesize_is_separate_endpoint,
              test_pdf_export_from_results]:
        t()
    print("\n✅ 5 tests revue de littérature passés.")
