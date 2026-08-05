"""Découpage intelligent de documents.

Stratégie : on respecte d'abord les frontières naturelles (paragraphes, puis
phrases) et on empile jusqu'à une taille cible en « tokens », avec un
recouvrement (overlap) pour ne pas couper le contexte à la jointure.

Estimation de tokens en Python pur (~mots) : évite la dépendance tiktoken tout
en restant proportionnel au vrai découpage BPE.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARA_SPLIT = re.compile(r"\n\s*\n")


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


@dataclass
class Chunk:
    ordinal: int
    text: str
    token_count: int = 0
    metadata: dict = field(default_factory=dict)


class RecursiveChunker:
    def __init__(self, chunk_tokens: int = 220, overlap_tokens: int = 40):
        if overlap_tokens >= chunk_tokens:
            raise ValueError("overlap doit être < chunk_tokens")
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens

    def _units(self, text: str) -> list[str]:
        """Découpe en unités atomiques (phrases), en respectant les paragraphes."""
        units: list[str] = []
        for para in _PARA_SPLIT.split(text.strip()):
            para = para.strip()
            if not para:
                continue
            for sent in _SENT_SPLIT.split(para):
                sent = sent.strip()
                if sent:
                    units.append(sent)
        return units

    def split(self, text: str) -> list[Chunk]:
        units = self._units(text)
        chunks: list[Chunk] = []
        buf: list[str] = []
        buf_tokens = 0
        ordinal = 0

        def flush():
            nonlocal buf, buf_tokens, ordinal
            if not buf:
                return
            body = " ".join(buf)
            chunks.append(Chunk(ordinal=ordinal, text=body,
                                token_count=estimate_tokens(body)))
            ordinal += 1
            # Recouvrement : on garde la fin du buffer pour le prochain chunk.
            if self.overlap_tokens and buf_tokens > self.overlap_tokens:
                kept, kt = [], 0
                for u in reversed(buf):
                    ut = estimate_tokens(u)
                    if kt + ut > self.overlap_tokens:
                        break
                    kept.insert(0, u)
                    kt += ut
                buf, buf_tokens = kept, kt
            else:
                buf, buf_tokens = [], 0

        for unit in units:
            ut = estimate_tokens(unit)
            if buf_tokens + ut > self.chunk_tokens and buf:
                flush()
            buf.append(unit)
            buf_tokens += ut
        # dernier morceau (sans réinjecter d'overlap)
        if buf:
            body = " ".join(buf)
            chunks.append(Chunk(ordinal=ordinal, text=body,
                                token_count=estimate_tokens(body)))
        return chunks
