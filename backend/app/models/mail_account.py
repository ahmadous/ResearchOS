"""Compte mail (IMAP) d'un utilisateur — mot de passe d'application CHIFFRÉ."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from ..security import decrypt, mask
from .base import TimestampMixin, UUIDMixin


class MailAccount(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "mail_accounts"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True,
                                         unique=True, nullable=False)   # un compte par user
    email: Mapped[str] = mapped_column(String(255))
    imap_host: Mapped[str] = mapped_column(String(120), default="imap.gmail.com")
    password_encrypted: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    @property
    def password(self) -> str:
        return decrypt(self.password_encrypted)

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "imap_host": self.imap_host,
                "password_masked": mask(self.password) if self.password_encrypted else None,
                "enabled": self.enabled, "created_at": self.created_at.isoformat()}
