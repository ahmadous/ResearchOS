"""Abstractions de la recherche scientifique.

Chaque base (arXiv, OpenAlex…) implémente `PaperSource` et normalise ses
résultats vers `Paper`. `parse()` est PUR (testable sans réseau) ; `_fetch()`
isole l'appel HTTP. Ajouter une source = une classe, rien d'autre à changer.
"""
from __future__ import annotations

import abc
import re
from dataclasses import asdict, dataclass, field

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


@dataclass
class Paper:
    title: str
    source: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    doi: str | None = None
    url: str | None = None
    venue: str | None = None
    citations: int | None = None
    external_id: str | None = None

    def key(self) -> str:
        """Clé de déduplication : DOI si présent, sinon titre normalisé."""
        if self.doi:
            return self.doi.lower().strip()
        return _NON_ALNUM.sub(" ", self.title.lower()).strip()

    def completeness(self) -> int:
        """Score de « richesse » pour départager deux doublons."""
        return (bool(self.abstract) * 3 + bool(self.doi) * 2
                + bool(self.year) + bool(self.authors)
                + (self.citations or 0) // 100)

    def to_dict(self) -> dict:
        return asdict(self)


class PaperSource(abc.ABC):
    name: str = "base"

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or self.default_base_url

    default_base_url: str = ""

    def search(self, query: str, limit: int = 10) -> list[Paper]:
        return self.parse(self._fetch(query, limit))

    @abc.abstractmethod
    def _fetch(self, query: str, limit: int):
        """Appel réseau — renvoie la réponse brute (dict JSON ou texte)."""

    @abc.abstractmethod
    def parse(self, raw) -> list[Paper]:
        """Transforme la réponse brute en liste de `Paper` (pur, sans réseau)."""
