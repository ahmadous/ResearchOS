"""Tests du moteur de workflow — tri topologique (pur) + exécution HTTP.

L'exécution utilise un Ollama SIMULÉ (modèle présent + complétion sans réseau).
Lancer :  python tests/test_workflow.py
"""
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.ai.base import CompletionResponse, Usage
from app.ai.providers.ollama_provider import OllamaProvider
from app.workflows import topological_order
from app.workflows.graph import WorkflowError

FAKE_INSTALLED = [{"name": "llama3.2:3b", "details": {"parameter_size": "3.2B"}}]


# --- Tri topologique (pur) ---
def test_topological_order_linear():
    g = {"nodes": [{"id": "a", "agent": "research"}, {"id": "b", "agent": "writing"},
                   {"id": "c", "agent": "reviewer"}],
         "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}]}
    order = [n["id"] for n in topological_order(g)]
    assert order == ["a", "b", "c"]
    print(f"[topo]     ordre linéaire: {order}")


def test_topological_order_respects_deps():
    # b et c dépendent de a ; d dépend de b et c. 'a' avant tout, 'd' en dernier.
    g = {"nodes": [{"id": n, "agent": "research"} for n in "abcd"],
         "edges": [{"source": "a", "target": "b"}, {"source": "a", "target": "c"},
                   {"source": "b", "target": "d"}, {"source": "c", "target": "d"}]}
    order = [n["id"] for n in topological_order(g)]
    assert order[0] == "a" and order[-1] == "d"
    print(f"[topo]     dépendances respectées: {order}")


def test_cycle_detected():
    g = {"nodes": [{"id": "a", "agent": "x"}, {"id": "b", "agent": "y"}],
         "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]}
    try:
        topological_order(g)
        assert False
    except WorkflowError as e:
        assert "Cycle" in str(e)
        print("[topo]     cycle -> WorkflowError")


# --- Exécution HTTP ---
def _fake_complete(self, request):
    return CompletionResponse(content=f"sortie de {request.model}",
                              model=request.model or "llama3.2:3b", provider="ollama",
                              usage=Usage(10, 8), cost_usd=0.0)


@contextmanager
def fake_ollama():
    with patch.object(OllamaProvider, "_fetch_installed", return_value=FAKE_INSTALLED), \
         patch.object(OllamaProvider, "complete", _fake_complete):
        yield


def _auth():
    c = create_app("test").test_client()
    r = c.post("/api/auth/register", json={"email": "wf@u.sn", "password": "motdepasse123"})
    return c, {"Authorization": f"Bearer {r.get_json()['access_token']}"}


def test_crud_and_run():
    c, h = _auth()
    graph = {"nodes": [{"id": "n1", "agent": "research", "task": "explorer"},
                       {"id": "n2", "agent": "writing", "task": "rédiger"}],
             "edges": [{"source": "n1", "target": "n2"}]}
    wf = c.post("/api/workflows", headers=h, json={"name": "Revue", "graph": graph}).get_json()
    assert wf["name"] == "Revue" and len(wf["graph"]["nodes"]) == 2
    print(f"[crud]     workflow créé ({wf['id'][:8]})")

    lst = c.get("/api/workflows", headers=h).get_json()["workflows"]
    assert any(w["id"] == wf["id"] for w in lst)

    with fake_ollama():
        run = c.post(f"/api/workflows/{wf['id']}/run", headers=h)
    body = run.get_json()
    assert run.status_code == 202 and body["status"] == "completed", body
    results = body["result"]["results"]
    assert [r["node_id"] for r in results] == ["n1", "n2"]     # ordre topologique
    assert all("content" in r for r in results)
    print(f"[run]      exécuté dans l'ordre: {[r['agent'] for r in results]}")


def test_run_rejects_cycle():
    c, h = _auth()
    graph = {"nodes": [{"id": "a", "agent": "research"}, {"id": "b", "agent": "writing"}],
             "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]}
    wf = c.post("/api/workflows", headers=h, json={"name": "Cyclique", "graph": graph}).get_json()
    with fake_ollama():
        run = c.post(f"/api/workflows/{wf['id']}/run", headers=h).get_json()
    assert run["status"] == "failed" and "Cycle" in (run["error"] or "")
    print("[run]      cycle -> tâche 'failed' propre")


if __name__ == "__main__":
    for t in [test_topological_order_linear, test_topological_order_respects_deps,
              test_cycle_detected, test_crud_and_run, test_run_rejects_cycle]:
        t()
    print("\n✅ 5 tests workflow passés.")
