"""Tests des agents et de l'orchestration — LLM SIMULÉ, aucun réseau.

Valide : catalogue d'agents, exécution unitaire, pipeline avec partage de
contexte (Blackboard), et mode auto (Planning décompose puis délègue).
Lancer :  python tests/test_agents.py   (depuis backend/)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import AgentLLMResponse, AgentRegistry, Orchestrator


class FakeLLM:
    """LLMClient factice : réponses scriptées, enregistre les appels."""

    def __init__(self, plan=None):
        self.calls = []
        self.plan = plan or [
            {"agent": "research", "task": "explorer le sujet"},
            {"agent": "writing", "task": "rédiger la synthèse"},
        ]

    def complete(self, messages, *, strategy="balanced", require_privacy=None,
                 pinned_model=None, agent=None):
        saw_ctx = any("Contexte produit par les autres agents" in m.content
                      for m in messages)
        self.calls.append({"agent": agent, "strategy": strategy, "saw_ctx": saw_ctx})
        content = json.dumps(self.plan) if agent == "planning" else f"[{agent}] ok ctx={saw_ctx}"
        return AgentLLMResponse(content=content, model="fake", provider="fake",
                                prompt_tokens=3, completion_tokens=5)


def orch(fake=None):
    return Orchestrator(AgentRegistry(fake or FakeLLM()))


def test_catalog_has_all_agents():
    o = orch()
    names = o.registry.names()
    assert "planning" in names and "research" in names and "citation" in names
    assert len(names) == 15, names        # 14 spécialisés + planning
    print(f"[catalog]  {len(names)} agents disponibles")


def test_run_single_agent():
    o = orch()
    r = o.run("research", "les transformers en NLP")
    assert r.agent == "research" and "[research]" in r.content
    print(f"[run]      research -> {r.content}")


def test_agent_uses_its_routing_strategy():
    fake = FakeLLM()
    orch(fake).run("translation", "traduire")
    # translation préfère la stratégie 'cost' (modèles locaux gratuits)
    assert fake.calls[-1]["strategy"] == "cost"
    print("[routing]  translation -> stratégie 'cost' propagée au routeur")


def test_pipeline_shares_context():
    """Le 2e agent doit VOIR la sortie du 1er (communication via Blackboard)."""
    fake = FakeLLM()
    res = orch(fake).pipeline(
        [{"agent": "writing", "task": "écrire"},
         {"agent": "reviewer", "task": "relire"}], goal="produire une section")
    writing, reviewer = res["results"]
    assert writing["content"] == "[writing] ok ctx=False"      # rien avant lui
    assert reviewer["content"] == "[reviewer] ok ctx=True"     # a vu writing
    print("[pipeline] reviewer a bien reçu le contexte de writing")


def test_auto_planning_decomposes_and_delegates():
    fake = FakeLLM(plan=[
        {"agent": "research", "task": "état de l'art"},
        {"agent": "writing", "task": "rédiger"},
    ])
    out = orch(fake).auto("Faire une revue sur les LLM", max_steps=5)
    dispatched = [c["agent"] for c in fake.calls]
    assert dispatched[0] == "planning"                # planification d'abord
    assert "research" in dispatched and "writing" in dispatched  # délégation
    assert len(out["results"]) == 3                   # planning + 2 étapes
    assert out["plan"][0]["agent"] == "research"
    print(f"[auto]     planning -> {[s['agent'] for s in out['plan']]} (agents collaborent)")


def test_auto_ignores_unknown_agents_in_plan():
    fake = FakeLLM(plan=[{"agent": "inexistant", "task": "x"},
                         {"agent": "summarizer", "task": "résumer"}])
    out = orch(fake).auto("objectif")
    agents_run = [c["agent"] for c in fake.calls]
    assert "inexistant" not in agents_run and "summarizer" in agents_run
    print("[robuste]  étape vers agent inconnu ignorée proprement")


def test_unknown_agent_raises():
    try:
        orch().run("does_not_exist", "x")
        assert False, "aurait dû lever"
    except KeyError:
        print("[error]    agent inconnu -> KeyError")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests d'agents passés.")
