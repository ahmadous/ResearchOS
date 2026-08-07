"""Service Revue de littérature — OUTIL de recherche, SANS état, immédiat.

Tu tapes un sujet -> recherche multi-sources RÉELLE (en parallèle) -> on renvoie
directement les articles (titre, auteurs, année, citations, DOI, lien, résumé),
le BibTeX et, en option, une courte synthèse IA. Rien n'est « généré » à la place
du chercheur : ce sont les vraies données, affichables et exportables.
"""
from __future__ import annotations

from ..ai.base import Message
from ..reports import render_digest_pdf, to_bibtex
from .agent_service import RouterLLMClient
from .llm_service import LLMService, LLMServiceError
from .scholar_service import ScholarService

_DEFAULT_SOURCES = ["arxiv", "openalex", "crossref"]

_SYNTH_SYSTEM = (
    "Tu es un assistant de recherche. En 4 à 6 puces FACTUELLES et concises, "
    "résume les tendances communes et les différences entre les articles fournis. "
    "Cite les numéros [n]. N'invente rien, appuie-toi UNIQUEMENT sur les résumés."
)


class ReportService:
    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    @staticmethod
    def _ref(p: dict) -> dict:
        return {"title": p.get("title"), "authors": p.get("authors", []),
                "year": p.get("year"), "venue": p.get("venue"),
                "citations": p.get("citations"), "doi": p.get("doi"),
                "url": p.get("url"), "source": p.get("source"),
                "abstract": p.get("abstract", "")}

    def search(self, user_id: str, query: str, *, sources: list[str] | None = None,
               limit: int = 10) -> dict:
        """Recherche pure et rapide — NE dépend JAMAIS du LLM (pas de 500 possible)."""
        if not query.strip():
            raise LLMServiceError("Requête vide")
        found = ScholarService().search(query, sources or _DEFAULT_SOURCES, limit)
        papers = found["results"][:limit]
        refs = [self._ref(p) for p in papers]
        return {"query": query, "count": len(refs), "results": refs,
                "errors": found.get("errors", {}), "bibtex": to_bibtex(papers)}

    def synthesize(self, user_id: str, query: str, papers: list[dict],
                   pinned_model: str | None = None) -> str:
        """Synthèse IA OPTIONNELLE, appelée séparément (peut être lente sur CPU)."""
        if not papers:
            raise LLMServiceError("Aucun article à synthétiser")
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError("Aucun modèle disponible pour la synthèse")
        blocks = [f"[{i}] {p.get('title')} ({p.get('year') or 's.d.'}): "
                  f"{(p.get('abstract') or '')[:300]}" for i, p in enumerate(papers, 1)]
        resp = RouterLLMClient(user_id, self.llm_service).complete(
            [Message("system", _SYNTH_SYSTEM),
             Message("user", f"Sujet : {query}\n\n" + "\n\n".join(blocks))],
            strategy="balanced", pinned_model=pinned_model, agent="research",
            max_tokens=350)
        return resp.content

    def render_pdf(self, query: str, papers: list[dict], synthesis: str = "") -> bytes:
        return render_digest_pdf(query, papers, synthesis)
