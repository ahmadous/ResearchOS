"""Memory Engine : faits persistants, rappelés sémantiquement entre sessions."""
from __future__ import annotations

import json

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin

# Portées possibles d'un souvenir.
SCOPES = ("user", "project", "agent", "global")


class MemoryItem(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "memory_items"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="user", index=True)
    project: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    agent: Mapped[str | None] = mapped_column(String(60), nullable=True)
    kind: Mapped[str] = mapped_column(String(30), default="fact")   # fact|preference|note
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")

    @property
    def embedding(self) -> list[float]:
        try:
            return json.loads(self.embedding_json or "[]")
        except json.JSONDecodeError:
            return []

    @embedding.setter
    def embedding(self, vec: list[float]) -> None:
        self.embedding_json = json.dumps(vec)

    def to_dict(self) -> dict:
        return {"id": self.id, "scope": self.scope, "project": self.project,
                "agent": self.agent, "kind": self.kind, "content": self.content,
                "created_at": self.created_at.isoformat()}
