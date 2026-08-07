from __future__ import annotations

from sqlalchemy import func

from ..extensions import db
from ..models import (
    ChatMessage, Chunk, Conversation, Document, GraphEntity, GraphRelation,
    MemoryItem, ModelUsage, ProviderCredential, Report, Task, User, Workflow,
)
from ..models.graph_entity import normalize
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def by_email(self, email: str) -> User | None:
        return self.first(email=email.lower().strip())


class ProviderRepository(BaseRepository[ProviderCredential]):
    model = ProviderCredential

    def for_user(self, user_id: str) -> list[ProviderCredential]:
        return self.list(user_id=user_id)

    def enabled_for_user(self, user_id: str) -> list[ProviderCredential]:
        return self.list(user_id=user_id, enabled=True)

    def default_for_user(self, user_id: str) -> ProviderCredential | None:
        return self.first(user_id=user_id, is_default=True)


class UsageRepository(BaseRepository[ModelUsage]):
    model = ModelUsage

    def summary_for_user(self, user_id: str) -> dict:
        row = db.session.execute(
            db.select(
                func.count(ModelUsage.id),
                func.coalesce(func.sum(ModelUsage.cost_usd), 0.0),
                func.coalesce(func.sum(ModelUsage.prompt_tokens
                                       + ModelUsage.completion_tokens), 0),
                func.coalesce(func.avg(ModelUsage.latency_ms), 0.0),
            ).where(ModelUsage.user_id == user_id)
        ).one()
        return {
            "calls": row[0],
            "total_cost_usd": round(row[1], 6),
            "total_tokens": int(row[2]),
            "avg_latency_ms": round(row[3], 1),
        }

    def by_model_for_user(self, user_id: str) -> list[dict]:
        rows = db.session.execute(
            db.select(
                ModelUsage.model,
                ModelUsage.provider,
                func.count(ModelUsage.id),
                func.coalesce(func.sum(ModelUsage.cost_usd), 0.0),
            ).where(ModelUsage.user_id == user_id)
            .group_by(ModelUsage.model, ModelUsage.provider)
        ).all()
        return [{"model": r[0], "provider": r[1], "calls": r[2],
                 "cost_usd": round(r[3], 6)} for r in rows]


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def for_user(self, user_id: str) -> list[Document]:
        return self.list(user_id=user_id)


class ChunkRepository(BaseRepository[Chunk]):
    model = Chunk

    def records_for_user(self, user_id: str) -> list[dict]:
        """Tous les chunks de l'utilisateur au format attendu par le retriever."""
        rows = db.session.execute(
            db.select(Chunk, Document.title)
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.user_id == user_id)
        ).all()
        return [chunk.to_record(title=title) for chunk, title in rows]

    def records_for_document(self, document_id: str, title: str | None = None) -> list[dict]:
        return [c.to_record(title=title) for c in self.list(document_id=document_id)]


class TaskRepository(BaseRepository[Task]):
    model = Task

    def for_user(self, user_id: str) -> list[Task]:
        rows = self.list(user_id=user_id)
        return sorted(rows, key=lambda t: t.created_at, reverse=True)


class WorkflowRepository(BaseRepository[Workflow]):
    model = Workflow

    def for_user(self, user_id: str) -> list[Workflow]:
        return sorted(self.list(user_id=user_id),
                      key=lambda w: w.updated_at, reverse=True)


class GraphRepository:
    """Accès au knowledge graph, avec upsert (fusion) des entités/relations."""

    def upsert_entity(self, user_id: str, name: str, etype: str) -> GraphEntity:
        norm = normalize(name)
        existing = db.session.scalars(
            db.select(GraphEntity).filter_by(user_id=user_id, norm_name=norm, type=etype)
        ).first()
        if existing:
            existing.mentions += 1
            return existing
        ent = GraphEntity(user_id=user_id, name=name, norm_name=norm, type=etype)
        db.session.add(ent)
        db.session.flush()   # matérialise l'id pour les relations
        return ent

    def upsert_relation(self, user_id: str, source_id: str, target_id: str,
                        label: str) -> GraphRelation:
        existing = db.session.scalars(
            db.select(GraphRelation).filter_by(
                user_id=user_id, source_id=source_id, target_id=target_id, label=label)
        ).first()
        if existing:
            existing.weight += 1
            return existing
        rel = GraphRelation(user_id=user_id, source_id=source_id,
                            target_id=target_id, label=label)
        db.session.add(rel)
        return rel

    def entities(self, user_id: str) -> list[GraphEntity]:
        return list(db.session.scalars(
            db.select(GraphEntity).filter_by(user_id=user_id)).all())

    def relations(self, user_id: str) -> list[GraphRelation]:
        return list(db.session.scalars(
            db.select(GraphRelation).filter_by(user_id=user_id)).all())

    def clear(self, user_id: str) -> None:
        for r in self.relations(user_id):
            db.session.delete(r)
        for e in self.entities(user_id):
            db.session.delete(e)
        db.session.commit()

    def commit(self) -> None:
        db.session.commit()


class MemoryRepository(BaseRepository[MemoryItem]):
    model = MemoryItem

    def for_user(self, user_id: str, *, scope: str | None = None,
                 project: str | None = None) -> list[MemoryItem]:
        filters = {"user_id": user_id}
        if scope:
            filters["scope"] = scope
        if project:
            filters["project"] = project
        return sorted(self.list(**filters), key=lambda m: m.created_at, reverse=True)


class ReportRepository(BaseRepository[Report]):
    model = Report

    def for_user(self, user_id: str) -> list[Report]:
        return sorted(self.list(user_id=user_id),
                      key=lambda r: r.created_at, reverse=True)


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    def for_user(self, user_id: str) -> list[Conversation]:
        return sorted(self.list(user_id=user_id),
                      key=lambda c: c.updated_at, reverse=True)


__all__ = ["UserRepository", "ProviderRepository", "UsageRepository",
           "DocumentRepository", "ChunkRepository", "TaskRepository",
           "WorkflowRepository", "GraphRepository", "MemoryRepository",
           "ReportRepository", "ConversationRepository"]
