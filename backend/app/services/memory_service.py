"""Memory Engine — mémorisation + rappel sémantique (sans appel LLM).

Le rappel est une recherche cosinus sur les embeddings des souvenirs (même
embedder que le RAG). Filtrable par portée (user/project/agent/global).
"""
from __future__ import annotations

from flask import current_app

from ..models import MemoryItem
from ..models.memory import SCOPES
from ..rag import cosine, get_embedder
from ..repositories import MemoryRepository
from .llm_service import LLMServiceError


class MemoryService:
    def __init__(self, repo: MemoryRepository | None = None):
        self.repo = repo or MemoryRepository()

    def _embedder(self):
        return get_embedder(
            current_app.config.get("EMBEDDING_BACKEND", "hashing"),
            model=current_app.config.get("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=current_app.config.get("OLLAMA_URL", "http://localhost:11434"))

    # --- Écriture ---
    def remember(self, user_id: str, content: str, *, scope: str = "user",
                 project: str | None = None, agent: str | None = None,
                 kind: str = "fact") -> dict:
        content = (content or "").strip()
        if not content:
            raise LLMServiceError("Souvenir vide")
        if scope not in SCOPES:
            raise LLMServiceError(f"Portée invalide: {scope}")
        item = MemoryItem(user_id=user_id, content=content, scope=scope,
                          project=project, agent=agent, kind=kind)
        item.embedding = self._embedder().embed(content)
        self.repo.add(item)
        return item.to_dict()

    # --- Lecture ---
    def list(self, user_id: str, *, scope: str | None = None,
             project: str | None = None) -> list[dict]:
        return [m.to_dict() for m in self.repo.for_user(user_id, scope=scope, project=project)]

    def recall(self, user_id: str, query: str, *, k: int = 5,
               scope: str | None = None, project: str | None = None,
               min_score: float = 0.15) -> list[dict]:
        """Souvenirs les plus proches de la requête (cosinus), triés décroissant."""
        items = self.repo.for_user(user_id, scope=scope, project=project)
        if not items or not query.strip():
            return []
        q = self._embedder().embed(query)
        scored = [(cosine(q, m.embedding), m) for m in items]
        scored = [(s, m) for s, m in scored if s >= min_score]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{**m.to_dict(), "score": round(s, 4)} for s, m in scored[:k]]

    def delete(self, user_id: str, item_id: str) -> None:
        item = self.repo.get(item_id)
        if not item or item.user_id != user_id:
            raise LLMServiceError("Souvenir introuvable")
        self.repo.delete(item)

    def clear(self, user_id: str, *, scope: str | None = None) -> int:
        items = self.repo.for_user(user_id, scope=scope)
        for m in items:
            self.repo.delete(m, commit=False)
        self.repo.commit()
        return len(items)

    # --- Utilisé par le chat pour injecter la mémoire pertinente ---
    def recall_context(self, user_id: str, query: str, k: int = 5) -> str:
        hits = self.recall(user_id, query, k=k)
        if not hits:
            return ""
        lines = "\n".join(f"- {h['content']}" for h in hits)
        return f"Éléments mémorisés pertinents (à prendre en compte) :\n{lines}"
