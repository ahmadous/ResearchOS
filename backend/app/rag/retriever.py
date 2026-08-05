"""Recherche hybride : dense (cosine) + sparse (BM25), fusionnés par RRF.

Reciprocal Rank Fusion : chaque système vote via le RANG (pas le score brut),
ce qui évite d'avoir à normaliser des échelles hétérogènes. Robuste et sans
paramètre sensible.
"""
from __future__ import annotations

from dataclasses import dataclass

from .bm25 import BM25


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


@dataclass
class Hit:
    record: dict          # {id, text, embedding, metadata...}
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None


def _ranking(scores: list[float]) -> dict[int, int]:
    """index -> rang (1 = meilleur), sur scores décroissants."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return {idx: rank + 1 for rank, idx in enumerate(order)}


def hybrid_search(query: str, query_embedding: list[float], records: list[dict],
                  *, k: int = 4, rrf_k: int = 60,
                  dense_weight: float = 1.0, sparse_weight: float = 1.0) -> list[Hit]:
    if not records:
        return []

    dense_scores = [cosine(query_embedding, r.get("embedding") or []) for r in records]
    sparse_scores = BM25([r.get("text", "") for r in records]).scores(query)

    dense_rank = _ranking(dense_scores)
    sparse_rank = _ranking(sparse_scores)

    hits: list[Hit] = []
    for i, rec in enumerate(records):
        fused = (dense_weight / (rrf_k + dense_rank[i])
                 + sparse_weight / (rrf_k + sparse_rank[i]))
        hits.append(Hit(record=rec, score=fused,
                        dense_rank=dense_rank[i], sparse_rank=sparse_rank[i]))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:k]
