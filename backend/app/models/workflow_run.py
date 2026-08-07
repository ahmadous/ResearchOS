"""Exécution d'un workflow — état pausable/reprenable."""
from __future__ import annotations

import json

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin

# Statuts d'une exécution.
PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELED = (
    "pending", "running", "paused", "completed", "failed", "canceled")


class WorkflowRun(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "workflow_runs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default=PENDING, index=True)
    step: Mapped[int] = mapped_column(Integer, default=0)        # prochain nœud à exécuter
    total: Mapped[int] = mapped_column(Integer, default=0)
    results_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    @property
    def results(self) -> list:
        try:
            return json.loads(self.results_json or "[]")
        except json.JSONDecodeError:
            return []

    @results.setter
    def results(self, value: list) -> None:
        self.results_json = json.dumps(value)

    def to_dict(self, *, full: bool = False) -> dict:
        d = {"id": self.id, "workflow_id": self.workflow_id, "name": self.name,
             "status": self.status, "step": self.step, "total": self.total,
             "error": self.error, "updated_at": self.updated_at.isoformat()}
        if full:
            d["results"] = self.results
        return d
