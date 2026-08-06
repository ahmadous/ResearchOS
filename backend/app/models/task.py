"""Tâches asynchrones — trace persistante de l'exécution des jobs longs."""
from __future__ import annotations

import json

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin

# Statuts possibles d'une tâche.
PENDING, RUNNING, COMPLETED, FAILED = "pending", "running", "completed", "failed"


class Task(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "tasks"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40))          # agent | rag_ingest | scholar_import
    status: Mapped[str] = mapped_column(String(20), default=PENDING, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)   # 0..100
    message: Mapped[str] = mapped_column(String(300), default="")
    result_json: Mapped[str] = mapped_column(Text, default="null")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def result(self):
        try:
            return json.loads(self.result_json or "null")
        except json.JSONDecodeError:
            return None

    @result.setter
    def result(self, value):
        self.result_json = json.dumps(value)

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "status": self.status,
                "progress": self.progress, "message": self.message,
                "result": self.result, "error": self.error,
                "created_at": self.created_at.isoformat()}
