"""Moteur RAG — orchestre chunking, embeddings, recherche et génération citée.

Reste PUR (aucune dépendance Flask/DB) : il reçoit un `embedder` et un `llm`
(interface LLMClient des agents). Testable avec un embedder déterministe et un
LLM factice.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..agents.base import LLMClient
from ..ai.base import Message
from .chunking import Chunk, RecursiveChunker
from .embeddings import Embedder
from .retriever import Hit, hybrid_search

_SYSTEM = (
    "Tu réponds UNIQUEMENT à partir du contexte fourni. Chaque affirmation doit "
    "être suivie de sa source au format [n] correspondant aux passages numérotés. "
    "Si le contexte ne permet pas de répondre, dis-le clairement."
)


@dataclass
class EmbeddedChunk:
    chunk: Chunk
    embedding: list[float] = field(default_factory=list)


class RAGEngine:
    def __init__(self, embedder: Embedder, llm: LLMClient, *,
                 chunk_tokens: int = 220, overlap_tokens: int = 40, top_k: int = 4):
        self.embedder = embedder
        self.llm = llm
        self.chunker = RecursiveChunker(chunk_tokens, overlap_tokens)
        self.top_k = top_k

    # --- Ingestion ---
    def chunk_and_embed(self, text: str) -> list[EmbeddedChunk]:
        chunks = self.chunker.split(text)
        embeddings = self.embedder.embed_many([c.text for c in chunks])
        return [EmbeddedChunk(c, e) for c, e in zip(chunks, embeddings)]

    # --- Interrogation ---
    def retrieve(self, question: str, records: list[dict]) -> list[Hit]:
        q_emb = self.embedder.embed(question)
        return hybrid_search(question, q_emb, records, k=self.top_k)

    @staticmethod
    def _build_context(hits: list[Hit]) -> tuple[str, list[dict]]:
        blocks, refs = [], []
        for n, hit in enumerate(hits, start=1):
            rec = hit.record
            blocks.append(f"[{n}] {rec.get('text', '')}")
            refs.append({
                "marker": n,
                "chunk_id": rec.get("id"),
                "document_id": rec.get("document_id"),
                "title": rec.get("title"),
                "ordinal": rec.get("ordinal"),
                "score": round(hit.score, 5),
                "snippet": (rec.get("text", "")[:200]),
            })
        return "\n\n".join(blocks), refs

    def answer(self, question: str, records: list[dict], *,
               strategy: str = "balanced", require_privacy: str | None = None,
               system_extra: str = "") -> dict:
        hits = self.retrieve(question, records)
        if not hits:
            return {"answer": "Aucun document indexé ne permet de répondre.",
                    "references": [], "used_chunks": 0}
        context, refs = self._build_context(hits)
        messages = [
            Message("system", _SYSTEM + system_extra),   # ex: consigne de langue
            Message("user", f"Contexte :\n{context}\n\nQuestion : {question}"),
        ]
        resp = self.llm.complete(messages, strategy=strategy,
                                 require_privacy=require_privacy, agent="rag")
        return {
            "answer": resp.content,
            "references": refs,
            "used_chunks": len(hits),
            "model": resp.model,
            "provider": resp.provider,
        }
