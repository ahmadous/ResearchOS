"""Agrégateur multi-sources : interroge plusieurs bases, déduplique, classe.

Robuste : l'échec d'une source (réseau/format) n'interrompt pas les autres.
"""
from __future__ import annotations

import logging

from .base import Paper, PaperSource
from .sources import SOURCES

log = logging.getLogger("researchos.scholar")


class ScholarAggregator:
    def __init__(self, sources: list[PaperSource] | None = None):
        # Par défaut : toutes les sources ouvertes.
        self.sources = sources or [cls() for cls in SOURCES.values()]

    @classmethod
    def from_names(cls, names: list[str]) -> "ScholarAggregator":
        chosen = [SOURCES[n]() for n in names if n in SOURCES]
        return cls(chosen or None)

    @staticmethod
    def available() -> list[str]:
        return sorted(SOURCES)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        collected: list[Paper] = []
        errors: dict[str, str] = {}
        for src in self.sources:
            try:
                collected.extend(src.search(query, limit))
            except Exception as e:                     # une source qui tombe n'arrête rien
                errors[src.name] = str(e)
                log.warning("source %s en échec: %s", src.name, e)
        merged = self._dedup(collected)
        merged.sort(key=lambda p: ((p.citations or 0), p.year or 0), reverse=True)
        return {"query": query, "count": len(merged),
                "results": [p.to_dict() for p in merged],
                "errors": errors}

    @staticmethod
    def _dedup(papers: list[Paper]) -> list[Paper]:
        """Fusionne les doublons (même DOI/titre) en gardant le plus complet."""
        best: dict[str, Paper] = {}
        for p in papers:
            k = p.key()
            if not k:
                continue
            cur = best.get(k)
            if cur is None or p.completeness() > cur.completeness():
                best[k] = p
        return list(best.values())
