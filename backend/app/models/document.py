"""Documents indexés + leurs chunks (avec embeddings) pour le RAG."""
from __future__ import annotations

import json

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db
from .base import TimestampMixin, UUIDMixin


class Document(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "documents"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), default="Sans titre")
    source_type: Mapped[str] = mapped_column(String(30), default="text")  # text|pdf|md|latex…
    source_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)  # url/chemin/doi
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)   # pièce jointe stockée
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    embedder: Mapped[str] = mapped_column(String(40), default="hashing")
    n_chunks: Mapped[int] = mapped_column(Integer, default=0)

    chunks = relationship("Chunk", back_populates="document",
                          cascade="all, delete-orphan")

    @property
    def is_attachment(self) -> bool:
        return bool(self.file_path)

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "source_type": self.source_type,
                "source_ref": self.source_ref, "embedder": self.embedder,
                "n_chunks": self.n_chunks, "mime_type": self.mime_type,
                "is_attachment": self.is_attachment,
                "created_at": self.created_at.isoformat()}


class Chunk(UUIDMixin, TimestampMixin, db.Model):
    __tablename__ = "chunks"

    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"),
                                             index=True, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[float]

    document = relationship("Document", back_populates="chunks")

    @property
    def embedding(self) -> list[float]:
        try:
            return json.loads(self.embedding_json or "[]")
        except json.JSONDecodeError:
            return []

    @embedding.setter
    def embedding(self, vec: list[float]) -> None:
        self.embedding_json = json.dumps(vec)

    def to_record(self, title: str | None = None) -> dict:
        """Format attendu par le retriever hybride."""
        return {"id": self.id, "text": self.text, "embedding": self.embedding,
                "document_id": self.document_id, "ordinal": self.ordinal,
                "title": title}
