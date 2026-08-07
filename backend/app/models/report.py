"""Rapports générés (état de l'art) à partir d'une recherche d'articles réelle."""
from __future__ import annotations

import json

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin


class Report(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "reports"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    query: Mapped[str] = mapped_column(String(400))
    title: Mapped[str] = mapped_column(String(400), default="Rapport")
    content: Mapped[str] = mapped_column(Text, default="")
    synthesis: Mapped[str] = mapped_column(Text, default="")   # synthèse IA OPTIONNELLE
    bibtex: Mapped[str] = mapped_column(Text, default="")
    references_json: Mapped[str] = mapped_column(Text, default="[]")
    n_sources: Mapped[int] = mapped_column(Integer, default=0)
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @property
    def references(self) -> list[dict]:
        try:
            return json.loads(self.references_json or "[]")
        except json.JSONDecodeError:
            return []

    @references.setter
    def references(self, value: list[dict]) -> None:
        self.references_json = json.dumps(value)

    def to_dict(self, *, full: bool = False) -> dict:
        d = {"id": self.id, "query": self.query, "title": self.title,
             "n_sources": self.n_sources, "has_pdf": bool(self.pdf_path),
             "created_at": self.created_at.isoformat()}
        d["has_synthesis"] = bool(self.synthesis)
        if full:
            d["content"] = self.content
            d["synthesis"] = self.synthesis
            d["references"] = self.references
        return d
