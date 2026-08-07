"""Tests des agents outillés — injection de VRAIES données via les outils.

Outils simulés (pas de réseau/DB). Vérifie que research/pdf/citation injectent
des données réelles dans le prompt et que graph fusionne dans le KG.
Lancer : python tests/test_tool_agents.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents import AgentRegistry, Orchestrator
from app.agents.base import AgentLLMResponse

FAKE_PAPERS = [
    {"title": "Flood CNN", "authors": ["A. Diop", "B. Sow"], "year": 2023,
     "abstract": "Un CNN pour la cartographie des inondations."},
    {"title": "SAR flood", "authors": ["C. Ndiaye"], "year": 2022, "abstract": "SAR."},
]


class FakeLLM:
    def __init__(self):
        self.last = None

    def complete(self, messages, **kw):
        self.last = " ".join(m.content for m in messages)
        return AgentLLMResponse(content="ok", model="fake", provider="fake")


def _tools(kg_calls):
    return {
        "scholar_search": lambda q, limit=6: FAKE_PAPERS,
        "rag_context": lambda q, k=4: "Extrait pertinent tiré de tes documents.",
        "kg_extract": lambda text: (kg_calls.append(text) or {
            "added_entities": 3, "added_relations": 2,
            "entities_total": 3, "relations_total": 2}),
    }


def test_research_injects_real_papers():
    fake = FakeLLM()
    Orchestrator(AgentRegistry(fake), tools=_tools([])).run("research", "inondations")
    assert "Flood CNN" in fake.last and "Articles réels" in fake.last
    print("[research] vraie recherche injectée dans le prompt")


def test_pdf_injects_rag_extracts():
    fake = FakeLLM()
    Orchestrator(AgentRegistry(fake), tools=_tools([])).run("pdf", "quelles méthodes ?")
    assert "Extrait pertinent" in fake.last
    print("[pdf]      extraits RAG injectés")


def test_citation_uses_real_papers():
    fake = FakeLLM()
    Orchestrator(AgentRegistry(fake), tools=_tools([])).run("citation", "cite le sujet")
    assert "Flood CNN" in fake.last and "à citer" in fake.last
    print("[citation] articles réels à citer injectés")


def test_graph_merges_into_kg():
    fake = FakeLLM()
    calls = []
    r = Orchestrator(AgentRegistry(fake), tools=_tools(calls)).run("graph", "texte source à analyser")
    assert calls and "texte source" in calls[0]         # kg_extract réellement appelé
    assert "fusionné dans le graphe" in fake.last        # confirmation dans le prompt
    print("[graph]    fusion réelle dans le Knowledge Graph")


def test_degrades_gracefully_without_tools():
    fake = FakeLLM()
    r = Orchestrator(AgentRegistry(fake)).run("research", "sans outils")  # aucun outil
    assert r.content == "ok" and "Articles réels" not in fake.last        # comportement LLM simple
    print("[fallback] sans outil -> comportement LLM normal (pas de crash)")


if __name__ == "__main__":
    for t in [test_research_injects_real_papers, test_pdf_injects_rag_extracts,
              test_citation_uses_real_papers, test_graph_merges_into_kg,
              test_degrades_gracefully_without_tools]:
        t()
    print("\n✅ 5 tests agents outillés passés.")
