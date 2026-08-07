"""Agents branchés sur de VRAIS outils (injectés via AgentContext.tools).

Chaque agent surcharge `preprocess` pour récupérer des données réelles (recherche
d'articles, extraits RAG, fusion Knowledge Graph) et les injecter dans le prompt
AVANT le LLM. Si l'outil est absent, l'agent se rabat sur son comportement LLM.
"""
from __future__ import annotations

from .base import AgentContext, BaseAgent


def _papers_block(papers: list[dict]) -> str:
    lines = []
    for i, p in enumerate(papers, 1):
        authors = ", ".join((p.get("authors") or [])[:3])
        lines.append(f"[{i}] {p.get('title')} — {authors} ({p.get('year') or 's.d.'})"
                     f" — {(p.get('abstract') or '')[:220]}")
    return "\n".join(lines)


class ResearchAgent(BaseAgent):
    name = "research"
    description = "Recherche RÉELLE d'articles (arXiv/OpenAlex/CrossRef) + synthèse"
    strategy = "quality"
    system_prompt = (
        "Tu es un agent de recherche. Synthétise l'état de l'art À PARTIR des "
        "articles réels fournis, en citant [n]. N'invente aucune référence.")

    def preprocess(self, task: str, ctx: AgentContext) -> str:
        papers = ctx.use_tool("scholar_search", task, limit=6) or []
        if not papers:
            return task
        ctx.data["papers"] = papers          # réutilisable par citation/graph
        return f"{task}\n\nArticles réels trouvés :\n{_papers_block(papers)}"


class WebSearchAgent(ResearchAgent):
    name = "web_search"
    description = "Recherche d'articles sur le web (bases scientifiques ouvertes)"
    strategy = "speed"


class PdfAgent(BaseAgent):
    name = "pdf"
    description = "Analyse tes documents importés (RAG) pour répondre"
    strategy = "quality"
    system_prompt = (
        "Tu es un agent d'analyse documentaire. Réponds à partir des EXTRAITS de "
        "documents fournis (méthodes, résultats, limites). Si vide, dis-le.")

    def preprocess(self, task: str, ctx: AgentContext) -> str:
        extracts = ctx.use_tool("rag_context", task) or ""
        return f"{task}\n\nExtraits de tes documents :\n{extracts}" if extracts else task


class CitationAgent(BaseAgent):
    name = "citation"
    description = "Citations RÉELLES (APA + BibTeX) à partir d'articles trouvés"
    strategy = "balanced"
    system_prompt = (
        "Tu es un agent de citation. À partir des articles fournis, produis les "
        "références au format APA. N'invente aucune référence.")

    def preprocess(self, task: str, ctx: AgentContext) -> str:
        papers = ctx.data.get("papers") or ctx.use_tool("scholar_search", task, limit=6) or []
        if not papers:
            return task
        ctx.data["papers"] = papers
        return f"{task}\n\nArticles à citer :\n{_papers_block(papers)}"


class GraphAgent(BaseAgent):
    name = "graph"
    description = "Extrait entités/relations et enrichit le Knowledge Graph RÉEL"
    strategy = "balanced"
    system_prompt = "Tu es un agent de graphe de connaissances."

    def preprocess(self, task: str, ctx: AgentContext) -> str:
        # Texte source = sorties des agents précédents, sinon la tâche.
        text = "\n".join(ctx.blackboard.values()) or task
        out = ctx.use_tool("kg_extract", text)
        if out:
            return (f"J'ai fusionné dans le graphe de connaissances "
                    f"{out.get('added_entities', 0)} entités et "
                    f"{out.get('added_relations', 0)} relations "
                    f"(total {out.get('entities_total', 0)} entités / "
                    f"{out.get('relations_total', 0)} relations). "
                    f"Résume en une phrase les entités clés de :\n{text[:500]}")
        return f"Extrais les entités et relations clés de :\n{text[:800]}"


TOOL_AGENTS = [ResearchAgent, WebSearchAgent, PdfAgent, CitationAgent, GraphAgent]
