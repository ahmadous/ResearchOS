"""Tests d'évaluation — evaluator pur + endpoint HTTP (Ollama simulé).

Lancer : python tests/test_evaluation.py
"""
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.agents.base import AgentLLMResponse
from app.ai.base import CompletionResponse, Usage
from app.ai.providers.ollama_provider import OllamaProvider
from app.evaluation import Evaluator

EVAL_JSON = {
    "confidence": 25, "verdict": "unreliable",
    "issues": ["L'article 'Attention Is All You Need' existe pourtant bien (2017).",
               "Aucune source fournie."],
    "correction": "Vaswani et al. (2017). Attention Is All You Need. NeurIPS.",
}


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.last_kwargs = None

    def complete(self, messages, **kw):
        self.last_kwargs = kw
        return AgentLLMResponse(content=self.payload, model="fake", provider="fake")


def test_evaluator_parses_structured_verdict():
    ev = Evaluator(FakeLLM(json.dumps(EVAL_JSON)))
    out = ev.evaluate("Cite l'article X", "Ce document n'existe pas.",
                      pinned_model="llama3.2:1b")
    assert out["confidence"] == 25 and out["verdict"] == "unreliable"
    assert len(out["issues"]) == 2 and out["correction"].startswith("Vaswani")
    print(f"[eval]     verdict={out['verdict']} conf={out['confidence']} issues={len(out['issues'])}")


def test_evaluator_infers_verdict_from_confidence():
    # Pas de verdict fourni -> déduit du score. Confiance haute -> reliable.
    ev = Evaluator(FakeLLM(json.dumps({"confidence": 90})))
    assert ev.evaluate("q", "a")["verdict"] == "reliable"
    print("[eval]     verdict déduit du score (90 -> reliable)")


def test_evaluator_handles_garbage():
    out = Evaluator(FakeLLM("je ne sais pas répondre en JSON")).evaluate("q", "a")
    assert out["verdict"] in ("reliable", "uncertain", "unreliable")
    assert 0 <= out["confidence"] <= 100
    print("[eval]     sortie non-JSON -> valeurs par défaut sûres")


def test_evaluator_passes_pinned_model():
    fake = FakeLLM(json.dumps({"confidence": 50}))
    Evaluator(fake).evaluate("q", "a", pinned_model="llama3.2:1b")
    assert fake.last_kwargs.get("pinned_model") == "llama3.2:1b"
    print("[eval]     pinned_model propagé au LLM")


# --- HTTP ---
def _fake_complete(self, request):
    return CompletionResponse(content=json.dumps(EVAL_JSON),
                              model=request.model or "llama3.2:1b", provider="ollama",
                              usage=Usage(20, 30), cost_usd=0.0)


@contextmanager
def fake_ollama():
    with patch.object(OllamaProvider, "_fetch_installed",
                      return_value=[{"name": "llama3.2:1b", "details": {"parameter_size": "1.2B"}}]), \
         patch.object(OllamaProvider, "complete", _fake_complete):
        yield


def test_evaluate_endpoint():
    c = create_app("test").test_client()
    tok = c.post("/api/auth/register",
                 json={"email": "ev@u.sn", "password": "motdepasse123"}).get_json()["access_token"]
    with fake_ollama():
        r = c.post("/api/evaluate", headers={"Authorization": f"Bearer {tok}"},
                   json={"question": "Cite l'article X", "answer": "Ce document n'existe pas."})
    body = r.get_json()
    assert r.status_code == 200, body
    assert body["verdict"] == "unreliable" and body["confidence"] == 25
    print(f"[http]     /evaluate -> {body['verdict']} ({body['confidence']}%)")


if __name__ == "__main__":
    for t in [test_evaluator_parses_structured_verdict, test_evaluator_infers_verdict_from_confidence,
              test_evaluator_handles_garbage, test_evaluator_passes_pinned_model,
              test_evaluate_endpoint]:
        t()
    print("\n✅ 5 tests évaluation passés.")
