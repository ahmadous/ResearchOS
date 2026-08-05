"""Télémétrie d'usage IA — alimentée par l'Observer du routeur.

Chaque appel LLM produit une ligne : modèle, provider, tokens, coût, latence.
C'est la source des dashboards de consommation du LLM Manager.
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .base import TimestampMixin, UUIDMixin


class ModelUsage(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "model_usage"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    model: Mapped[str] = mapped_column(String(80), index=True)

    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    agent: Mapped[str | None] = mapped_column(String(60), nullable=True)  # quel agent a appelé

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": round(self.latency_ms, 1),
            "agent": self.agent,
            "created_at": self.created_at.isoformat(),
        }
