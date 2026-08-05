"""Credential d'un fournisseur IA, propre à un utilisateur.

Un utilisateur peut enregistrer plusieurs providers, et pour chacun plusieurs
clés (ex: OpenAI perso + OpenAI labo). La clé est stockée CHIFFRÉE.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from ..security import decrypt, mask
from .base import TimestampMixin, UUIDMixin


class ProviderCredential(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "provider_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "provider_key", "label",
                         name="uq_user_provider_label"),
    )

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    provider_key: Mapped[str] = mapped_column(String(40), nullable=False)  # "openai"...
    label: Mapped[str] = mapped_column(String(80), default="default")      # nom lisible
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="credentials")

    @property
    def api_key(self) -> str:
        return decrypt(self.api_key_encrypted)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider_key": self.provider_key,
            "label": self.label,
            "api_key_masked": mask(self.api_key) if self.api_key_encrypted else None,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
        }
