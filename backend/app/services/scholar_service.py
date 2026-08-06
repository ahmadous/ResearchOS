"""Service de recherche scientifique + import vers le RAG.

Recherche multi-sources (arXiv, OpenAlex…) et ingestion d'un article (titre +
résumé) comme Document indexé, exploitable ensuite par les agents et le RAG.
"""
from __future__ import annotations

from ..scholar import ScholarAggregator
from .llm_service import LLMServiceError
from .rag_service import RAGService


class ScholarService:
    def __init__(self, rag: RAGService | None = None):
        self.rag = rag or RAGService()

    def available_sources(self) -> list[str]:
        return ScholarAggregator.available()

    def search(self, query: str, sources: list[str] | None = None,
               limit: int = 10) -> dict:
        agg = ScholarAggregator.from_names(sources) if sources else ScholarAggregator()
        return agg.search(query, limit)

    def import_paper(self, user_id: str, paper: dict) -> dict:
        title = (paper.get("title") or "").strip()
        abstract = (paper.get("abstract") or "").strip()
        if not title and not abstract:
            raise LLMServiceError("Article sans titre ni résumé : rien à indexer")
        authors = ", ".join(paper.get("authors") or [])
        # Corps indexé : métadonnées + résumé (le résumé porte l'essentiel du sens).
        body = "\n".join(filter(None, [
            f"Titre : {title}" if title else "",
            f"Auteurs : {authors}" if authors else "",
            f"Année : {paper['year']}" if paper.get("year") else "",
            f"Source : {paper.get('source')}",
            "", abstract or "(résumé indisponible)",
        ]))
        ref = paper.get("doi") or paper.get("url") or paper.get("external_id")
        return self.rag.ingest_text(
            user_id, title=title or "Article", text=body,
            source_type="paper", source_ref=ref)
