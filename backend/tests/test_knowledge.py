"""Tests Knowledge Graph — extracteur pur + extraction HTTP + fusion/dédup.

Ollama SIMULÉ (renvoie un JSON de graphe). Lancer : python tests/test_knowledge.py
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
from app.knowledge import KGExtractor

GRAPH_JSON = {
    "entities": [
        {"name": "Ashish Vaswani", "type": "author"},
        {"name": "Google Brain", "type": "institution"},
        {"name": "Transformer", "type": "algorithm"},
    ],
    "relations": [
        {"source": "Ashish Vaswani", "target": "Transformer", "label": "a proposé"},
        {"source": "Ashish Vaswani", "target": "Google Brain", "label": "affilié à"},
        {"source": "Transformer", "target": "Attention", "label": "utilise"},  # 'Attention' -> concept
    ],
}


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, messages, **kw):
        return AgentLLMResponse(content=self.payload, model="fake", provider="fake")


# --- Extracteur pur ---
def test_extractor_parses_and_creates_missing_concepts():
    ext = KGExtractor(FakeLLM(json.dumps(GRAPH_JSON)))
    data = ext.extract("un texte")
    names = {e["name"] for e in data["entities"]}
    assert {"Ashish Vaswani", "Transformer", "Google Brain", "Attention"} <= names
    # 'Attention' n'était que dans une relation -> ajouté comme concept
    assert any(e["name"] == "Attention" and e["type"] == "concept" for e in data["entities"])
    assert len(data["relations"]) == 3
    print(f"[extract]  {len(data['entities'])} entités, {len(data['relations'])} relations")


def test_extractor_handles_garbage():
    data = KGExtractor(FakeLLM("désolé je ne peux pas")).extract("x")
    assert data == {"entities": [], "relations": []}
    print("[extract]  sortie non-JSON -> graphe vide (pas de crash)")


# --- HTTP + fusion ---
def _fake_complete(self, request):
    return CompletionResponse(content=json.dumps(GRAPH_JSON),
                              model=request.model or "llama3.2:3b", provider="ollama",
                              usage=Usage(10, 30), cost_usd=0.0)


@contextmanager
def fake_ollama():
    with patch.object(OllamaProvider, "_fetch_installed",
                      return_value=[{"name": "llama3.2:3b", "details": {"parameter_size": "3.2B"}}]), \
         patch.object(OllamaProvider, "complete", _fake_complete):
        yield


def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "kg@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_extract_http_and_merge_dedup():
    c, h = _auth()
    with fake_ollama():
        r1 = c.post("/api/graph/extract", headers=h, json={"text": "Un article sur le Transformer."})
        assert r1.status_code == 202 and r1.get_json()["status"] == "completed", r1.get_json()
        # 4 entités (3 + 'Attention'), 3 relations
        assert r1.get_json()["result"]["entities_total"] == 4

        # Deuxième extraction identique -> DÉDUP : pas de nouvelles entités
        r2 = c.post("/api/graph/extract", headers=h, json={"text": "Encore le Transformer."})
        assert r2.get_json()["result"]["entities_total"] == 4

    g = c.get("/api/graph", headers=h).get_json()
    assert len(g["nodes"]) == 4 and len(g["edges"]) == 3
    # La dédup a incrémenté les mentions/poids plutôt que dupliquer.
    transformer = next(n for n in g["nodes"] if n["name"] == "Transformer")
    assert transformer["mentions"] == 2
    print(f"[http]     graphe: {len(g['nodes'])} nœuds, {len(g['edges'])} arêtes (dédup OK)")


def test_clear_graph():
    c, h = _auth()
    with fake_ollama():
        c.post("/api/graph/extract", headers=h, json={"text": "Transformer."})
    c.delete("/api/graph", headers=h)
    g = c.get("/api/graph", headers=h).get_json()
    assert g["nodes"] == [] and g["edges"] == []
    print("[http]     DELETE /graph -> graphe vidé")


if __name__ == "__main__":
    for t in [test_extractor_parses_and_creates_missing_concepts, test_extractor_handles_garbage,
              test_extract_http_and_merge_dedup, test_clear_graph]:
        t()
    print("\n✅ 4 tests knowledge graph passés.")
