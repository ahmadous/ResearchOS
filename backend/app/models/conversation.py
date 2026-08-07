"""Conversations de chat persistantes (retrouvées entre les sessions)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .base import TimestampMixin, UUIDMixin


class Conversation(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "conversations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="Nouvelle conversation")

    messages = relationship("ChatMessage", back_populates="conversation",
                            cascade="all, delete-orphan",
                            order_by="ChatMessage.created_at")

    def to_dict(self, *, with_messages: bool = False) -> dict:
        d = {"id": self.id, "title": self.title,
             "n_messages": len(self.messages),
             "updated_at": self.updated_at.isoformat()}
        if with_messages:
            d["messages"] = [m.to_dict() for m in self.messages]
        return d


class ChatMessage(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "chat_messages"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20))          # user | assistant
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)

    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self) -> dict:
        return {"id": self.id, "role": self.role, "content": self.content,
                "model": self.model, "created_at": self.created_at.isoformat()}
