"""Service Mail — connexion IMAP lecture seule + tri LLM (aucun envoi)."""
from __future__ import annotations

from ..extensions import db
from ..mail import IMAPConnector, MailError, MailTriager
from ..models import MailAccount
from ..security import encrypt
from .agent_service import RouterLLMClient
from .llm_service import LLMService, LLMServiceError


class MailService:
    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def _account(self, user_id: str) -> MailAccount | None:
        return db.session.scalars(
            db.select(MailAccount).filter_by(user_id=user_id)).first()

    def get_account(self, user_id: str) -> dict | None:
        acc = self._account(user_id)
        return acc.to_dict() if acc else None

    def connect_account(self, user_id: str, email: str, password: str,
                        imap_host: str = "imap.gmail.com") -> dict:
        # Valide les identifiants tout de suite (login IMAP).
        try:
            IMAPConnector(imap_host, email, password).check()
        except MailError as e:
            raise LLMServiceError(str(e))
        acc = self._account(user_id)
        if not acc:
            acc = MailAccount(user_id=user_id)
            db.session.add(acc)
        acc.email = email
        acc.imap_host = imap_host
        acc.password_encrypted = encrypt(password)
        acc.enabled = True
        db.session.commit()
        return acc.to_dict()

    def delete_account(self, user_id: str) -> None:
        acc = self._account(user_id)
        if acc:
            db.session.delete(acc)
            db.session.commit()

    def _connector(self, user_id: str) -> IMAPConnector:
        acc = self._account(user_id)
        if not acc:
            raise LLMServiceError("Aucun compte mail connecté")
        return IMAPConnector(acc.imap_host, acc.email, acc.password)

    def inbox(self, user_id: str, n: int = 20) -> dict:
        """Liste les N derniers mails — RAPIDE, aucun LLM."""
        try:
            emails = self._connector(user_id).fetch_recent(n)
        except MailError as e:
            raise LLMServiceError(str(e))
        return {"count": len(emails), "emails": emails}

    def triage(self, user_id: str, emails: list[dict],
               pinned_model: str | None = None) -> dict:
        """Trie les emails fournis par importance / à répondre (LLM, séparé)."""
        if not emails:
            return {"emails": []}
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError("Aucun modèle disponible pour le tri")
        triager = MailTriager(RouterLLMClient(user_id, self.llm_service))
        return {"emails": triager.classify(emails, pinned_model)}
