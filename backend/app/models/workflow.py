"""Workflow = graphe d'agents (nodes + edges) construit visuellement."""
from __future__ import annotations

import json

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin


class Workflow(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "workflows"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), default="Nouveau workflow")
    graph_json: Mapped[str] = mapped_column(Text, default='{"nodes": [], "edges": []}')

    @property
    def graph(self) -> dict:
        try:
            g = json.loads(self.graph_json or "{}")
        except json.JSONDecodeError:
            g = {}
        return {"nodes": g.get("nodes", []), "edges": g.get("edges", [])}

    @graph.setter
    def graph(self, value: dict) -> None:
        self.graph_json = json.dumps({"nodes": value.get("nodes", []),
                                      "edges": value.get("edges", [])})

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "graph": self.graph,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat()}
