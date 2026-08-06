"""Knowledge Graph : entités (auteurs, institutions, algos…) et relations.

Modèle normalisé pour permettre la DÉDUPLICATION et l'enrichissement progressif :
chaque nouvelle extraction fusionne dans le graphe existant de l'utilisateur.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin


def normalize(name: str) -> str:
    return " ".join((name or "").lower().split())


class GraphEntity(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "graph_entities"
    __table_args__ = (
        UniqueConstraint("user_id", "norm_name", "type", name="uq_entity"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200))
    norm_name: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(40), default="concept")  # author|institution|…
    mentions: Mapped[int] = mapped_column(Integer, default=1)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "type": self.type,
                "mentions": self.mentions}


class GraphRelation(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "graph_relations"
    __table_args__ = (
        UniqueConstraint("user_id", "source_id", "target_id", "label", name="uq_relation"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(ForeignKey("graph_entities.id"))
    target_id: Mapped[str] = mapped_column(ForeignKey("graph_entities.id"))
    label: Mapped[str] = mapped_column(String(80), default="lié à")
    weight: Mapped[int] = mapped_column(Integer, default=1)

    def to_dict(self) -> dict:
        return {"id": self.id, "source": self.source_id, "target": self.target_id,
                "label": self.label, "weight": self.weight}
