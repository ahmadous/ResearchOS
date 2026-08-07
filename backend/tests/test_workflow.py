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


# Agents SANS outils (LLM pur) -> pas de réseau dans les tests.
GRAPH = {"nodes": [{"id": "n1", "agent": "summarizer", "task": "résumer"},
                   {"id": "n2", "agent": "writing", "task": "rédiger"}],
         "edges": [{"source": "n1", "target": "n2"}]}


def test_crud_and_run():
    c, h = _auth()
    wf = c.post("/api/workflows", headers=h, json={"name": "Revue", "graph": GRAPH}).get_json()
    assert wf["name"] == "Revue" and len(wf["graph"]["nodes"]) == 2

    with fake_ollama():
        run = c.post(f"/api/workflows/{wf['id']}/run", headers=h)
    body = run.get_json()
    assert run.status_code == 202, body
    # /run renvoie {run, task} ; en test (runner sync) la tâche est déjà terminée.
    task = body["task"]
    assert task["status"] == "completed", task
    result = task["result"]
    assert result["status"] == "completed" and result["step"] == 2
    assert [r["node_id"] for r in result["results"]] == ["n1", "n2"]  # ordre topologique
    print(f"[run]      exécuté dans l'ordre: {[r['agent'] for r in result['results']]}")

    runs = c.get("/api/workflows/runs", headers=h).get_json()["runs"]
    assert len(runs) == 1 and runs[0]["status"] == "completed"
    print("[runs]     historique des exécutions listé")


def test_run_rejects_cycle():
    c, h = _auth()
    graph = {"nodes": [{"id": "a", "agent": "writing"}, {"id": "b", "agent": "summarizer"}],
             "edges": [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}]}
    wf = c.post("/api/workflows", headers=h, json={"name": "Cyclique", "graph": graph}).get_json()
    r = c.post(f"/api/workflows/{wf['id']}/run", headers=h)
    assert r.status_code == 400 and "Cycle" in r.get_json()["message"]
    print("[run]      cycle -> 400 dès la création du run")


def test_pause_stops_and_resume_completes():
    """L'exécuteur s'arrête si le run est en pause, et reprend jusqu'au bout."""
    from app.extensions import db
    from app.models import WorkflowRun
    from app.services import WorkflowService
    app = create_app("test")
    c = app.test_client()
    tok = c.post("/api/auth/register", json={"email": "pz@u.sn", "password": "motdepasse123"}).get_json()["access_token"]
    from flask_jwt_extended import decode_token
    with app.app_context():
        uid = decode_token(tok)["sub"]
        wf = WorkflowService().create(uid, "Pause test", GRAPH)
        svc = WorkflowService()
        run = svc.create_run(uid, wf["id"])
        with fake_ollama():
            # Pré-pause -> l'exécuteur ne doit lancer aucun nœud.
            r = db.session.get(WorkflowRun, run["id"]); r.status = "paused"; db.session.commit()
            out = svc.execute_run(uid, run["id"], "tid")
            assert out["status"] == "paused" and out["step"] == 0 and out["results"] == []
            # Reprise -> va jusqu'au bout.
            r = db.session.get(WorkflowRun, run["id"]); r.status = "running"; db.session.commit()
            done = svc.execute_run(uid, run["id"], "tid")
            assert done["status"] == "completed" and done["step"] == 2
    print("[pause]    pause stoppe (0 nœud) puis reprise termine (2 nœuds)")


if __name__ == "__main__":
    for t in [test_topological_order_linear, test_topological_order_respects_deps,
              test_cycle_detected, test_crud_and_run, test_run_rejects_cycle,
              test_pause_stops_and_resume_completes]:
        t()
    print("\n✅ 6 tests workflow passés.")
