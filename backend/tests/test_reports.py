"""Tests Rapports — rendu PDF pur + pipeline complet (recherche & LLM simulés).

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
from app.reports import render_report_pdf
from app.services.scholar_service import ScholarService

FAKE_PAPERS = {
    "count": 2, "errors": {},
    "results": [
        {"title": "Flood mapping with deep learning", "authors": ["A. Diop", "B. Sow"],
         "year": 2023, "url": "https://arxiv.org/abs/1", "source": "arxiv",
         "abstract": "We propose a CNN for flood mapping from satellite imagery."},
        {"title": "Sentinel-1 SAR flood detection", "authors": ["C. Ndiaye"],
         "year": 2022, "url": "https://openalex.org/W2", "source": "openalex",
         "abstract": "SAR-based flood detection over West Africa."},
    ],
}

REPORT_BODY = ("## Introduction\nLes inondations… [1]\n## Travaux existants\n"
               "Diop et al. utilisent un CNN [1]. Ndiaye exploite le SAR [2].\n"
               "## Comparaison\n[1] vs [2].\n## Research Gap\nManque de données locales.\n"
               "## Conclusion\nPistes futures.")


def test_render_pdf():
    pdf = render_report_pdf("Titre", "sous-titre", REPORT_BODY, FAKE_PAPERS["results"])
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1000
    print(f"[pdf]      PDF valide généré ({len(pdf)} octets)")


def _report_complete(self, request):
    return CompletionResponse(content=REPORT_BODY, model=request.model or "llama3.2:1b",
                              provider="ollama", usage=Usage(200, 300), cost_usd=0.0)


@contextmanager
def fake_backends():
    with patch.object(OllamaProvider, "_fetch_installed",
                      return_value=[{"name": "llama3.2:1b", "details": {"parameter_size": "1.2B"}}]), \
         patch.object(OllamaProvider, "complete", _report_complete), \
         patch.object(ScholarService, "search", return_value=FAKE_PAPERS):
        yield


def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "rep@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_generate_report_and_download_pdf():
    c, h = _auth()
    with fake_backends():
        r = c.post("/api/reports", headers=h, json={"query": "flood mapping satellite Senegal"})
    body = r.get_json()
    assert r.status_code == 202 and body["status"] == "completed", body
    result = body["result"]
    assert result["n_sources"] == 2 and "## Research Gap" in result["content"]
    print(f"[report]   généré : '{result['title'][:40]}…' ({result['n_sources']} sources)")

    # Liste + PDF téléchargeable
    reports = c.get("/api/reports", headers=h).get_json()["reports"]
    assert len(reports) == 1 and reports[0]["has_pdf"]
    pdf = c.get(f"/api/reports/{result['id']}/pdf", headers=h)
    assert pdf.status_code == 200 and pdf.data[:5] == b"%PDF-"
    assert pdf.headers["Content-Type"] == "application/pdf"
    print(f"[report]   PDF téléchargeable ({len(pdf.data)} octets)")


def test_report_no_results():
    c, h = _auth()
    with patch.object(OllamaProvider, "_fetch_installed",
                      return_value=[{"name": "llama3.2:1b", "details": {"parameter_size": "1.2B"}}]), \
         patch.object(ScholarService, "search", return_value={"count": 0, "results": [], "errors": {}}):
        r = c.post("/api/reports", headers=h, json={"query": "xyznoresults123"})
    assert r.get_json()["status"] == "failed" and "Aucun article" in (r.get_json()["error"] or "")
    print("[report]   aucun article -> tâche 'failed' propre")


if __name__ == "__main__":
    for t in [test_render_pdf, test_generate_report_and_download_pdf, test_report_no_results]:
        t()
    print("\n✅ 3 tests rapports passés.")
