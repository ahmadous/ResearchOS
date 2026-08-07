"""Service Conversations — persistance du chat (création, ajout, relecture)."""
from __future__ import annotations

from datetime import datetime, timezone

from ..extensions import db
from ..models import ChatMessage, Conversation
from ..repositories import ConversationRepository
from .llm_service import LLMServiceError


class ConversationService:
    def __init__(self, repo: ConversationRepository | None = None):
        self.repo = repo or ConversationRepository()

    def create(self, user_id: str, title: str | None = None) -> dict:
        conv = Conversation(user_id=user_id, title=(title or "Nouvelle conversation")[:200])
        self.repo.add(conv)
        return conv.to_dict()

    def list(self, user_id: str) -> list[dict]:
        return [c.to_dict() for c in self.repo.for_user(user_id)]

    def get(self, user_id: str, conv_id: str) -> dict:
        return self._owned(user_id, conv_id).to_dict(with_messages=True)

    def append(self, user_id: str, conv_id: str, role: str, content: str,
               model: str | None = None) -> dict:
        conv = self._owned(user_id, conv_id)
        conv.messages.append(ChatMessage(role=role, content=content, model=model))
        # Titre auto = premier message utilisateur.
        if conv.title == "Nouvelle conversation" and role == "user":
            conv.title = content.strip().split("\n")[0][:60] or conv.title
        conv.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return conv.to_dict()

    def rename(self, user_id: str, conv_id: str, title: str) -> dict:
        conv = self._owned(user_id, conv_id)
        conv.title = title[:200]
        db.session.commit()
        return conv.to_dict()

    def delete(self, user_id: str, conv_id: str) -> None:
        self.repo.delete(self._owned(user_id, conv_id))

    def _owned(self, user_id: str, conv_id: str) -> Conversation:
        conv = self.repo.get(conv_id)
        if not conv or conv.user_id != user_id:
            raise LLMServiceError("Conversation introuvable")
        return conv
