"""Service Rapports — recherche d'articles RÉELLE -> rédaction -> PDF.

Pipeline complet :
  1. recherche multi-sources (arXiv, OpenAlex… : vraies APIs web),
  2. synthèse structurée (état de l'art) par le LLM, avec citations [n],
  3. rendu PDF téléchargeable.
Exécuté en tâche asynchrone (progression WebSocket).
"""
from __future__ import annotations

import os

from flask import current_app

from ..ai.base import Message
from ..models import Report
from ..reports import render_report_pdf
from ..repositories import ReportRepository
from .agent_service import RouterLLMClient
from .llm_service import LLMService, LLMServiceError
from .scholar_service import ScholarService

_SYSTEM = (
    "Tu es un chercheur. À partir des articles NUMÉROTÉS fournis, rédige un mini "
    "état de l'art en français, structuré EXACTEMENT avec ces sections Markdown :\n"
    "## Introduction\n## Travaux existants\n## Comparaison\n## Research Gap\n## Conclusion\n"
    "Cite les sources par leur numéro entre crochets, ex: [1], [3]. Appuie-toi "
    "UNIQUEMENT sur les articles fournis, n'invente rien."
)


class ReportService:
    def __init__(self, llm_service: LLMService | None = None,
                 repo: ReportRepository | None = None):
        self.llm_service = llm_service or LLMService()
        self.repo = repo or ReportRepository()

    def _reports_dir(self) -> str:
        d = current_app.config["REPORTS_DIR"]
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def _context(papers: list[dict]) -> str:
        blocks = []
        for i, p in enumerate(papers, 1):
            authors = ", ".join(p.get("authors", [])[:3])
            abstract = (p.get("abstract") or "")[:600]
            blocks.append(f"[{i}] {p.get('title')} — {authors} ({p.get('year') or 's.d.'})"
                          f"\n{abstract}")
        return "\n\n".join(blocks)

    def generate(self, user_id: str, query: str, *, sources: list[str] | None = None,
                 limit: int = 8, pinned_model: str | None = None,
                 progress=lambda *_: None) -> dict:
        if not query.strip():
            raise LLMServiceError("Requête vide")
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError("Aucun modèle disponible pour rédiger le rapport")

        # 1) Recherche RÉELLE
        progress(15, "recherche d'articles…")
        found = ScholarService().search(query, sources, limit)
        papers = found["results"][:limit]
        if not papers:
            raise LLMServiceError("Aucun article trouvé pour cette requête")

        # 2) Rédaction (LLM)
        progress(45, f"rédaction à partir de {len(papers)} articles…")
        llm = RouterLLMClient(user_id, self.llm_service)
        resp = llm.complete(
            [Message("system", _SYSTEM),
             Message("user", f"Sujet : {query}\n\nArticles :\n{self._context(papers)}")],
            strategy="quality", pinned_model=pinned_model, agent="writing",
            max_tokens=700)   # borne le temps de génération (surtout sur CPU)
        content = resp.content

        # 3) Persistance + PDF
        progress(85, "génération du PDF…")
        refs = [{"authors": p.get("authors", []), "title": p.get("title"),
                 "year": p.get("year"), "url": p.get("url"), "source": p.get("source")}
                for p in papers]
        report = Report(user_id=user_id, query=query,
                        title=f"État de l'art : {query}"[:400],
                        content=content, n_sources=len(papers))
        report.references = refs
        self.repo.add(report)

        pdf = render_report_pdf(report.title, f"Généré par ResearchOS · {len(papers)} sources",
                                content, refs)
        path = os.path.join(self._reports_dir(), f"{report.id}.pdf")
        with open(path, "wb") as f:
            f.write(pdf)
        report.pdf_path = path
        self.repo.commit()
        progress(100, "terminé")
        return report.to_dict(full=True)

    # --- Lecture ---
    def list(self, user_id: str) -> list[dict]:
        return [r.to_dict() for r in self.repo.for_user(user_id)]

    def get(self, user_id: str, report_id: str, *, full: bool = True) -> dict:
        r = self._owned(user_id, report_id)
        return r.to_dict(full=full)

    def pdf_path(self, user_id: str, report_id: str) -> str:
        r = self._owned(user_id, report_id)
        if not r.pdf_path or not os.path.exists(r.pdf_path):
            raise LLMServiceError("PDF indisponible")
        return r.pdf_path

    def _owned(self, user_id: str, report_id: str) -> Report:
        r = self.repo.get(report_id)
        if not r or r.user_id != user_id:
            raise LLMServiceError("Rapport introuvable")
        return r
