"""Sources académiques concrètes (APIs ouvertes, sans clé).

Chaque `parse()` est pur et testé avec des payloads réels. Le réseau est confiné
dans `_fetch()` (via `_get`, qui suit les redirections et envoie un User-Agent poli).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from .base import Paper, PaperSource

_TIMEOUT = 10   # court : un outil de recherche doit rester réactif
_HEADERS = {"User-Agent": "ResearchOS/1.0 (mailto:research@researchos.dev)"}


def _get(url: str, params: dict):
    # follow_redirects : arXiv redirige http -> https.
    return httpx.get(url, params=params, timeout=_TIMEOUT,
                     follow_redirects=True, headers=_HEADERS)


class ArxivSource(PaperSource):
    name = "arxiv"
    default_base_url = "https://export.arxiv.org/api/query"
    _NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

    def _fetch(self, query, limit):
        r = _get(self.base_url, {"search_query": f"all:{query}", "max_results": limit})
        r.raise_for_status()
        return r.text

    def parse(self, raw: str) -> list[Paper]:
        root = ET.fromstring(raw)
        papers = []
        for e in root.findall("a:entry", self._NS):
            title = (e.findtext("a:title", default="", namespaces=self._NS) or "").strip()
            summary = (e.findtext("a:summary", default="", namespaces=self._NS) or "").strip()
            published = e.findtext("a:published", default="", namespaces=self._NS) or ""
            url = e.findtext("a:id", default="", namespaces=self._NS) or None
            doi = e.findtext("arxiv:doi", default=None, namespaces=self._NS)
            authors = [a.findtext("a:name", default="", namespaces=self._NS)
                       for a in e.findall("a:author", self._NS)]
            year = int(published[:4]) if published[:4].isdigit() else None
            papers.append(Paper(title=title, source=self.name, authors=authors,
                                year=year, abstract=summary, doi=doi, url=url,
                                external_id=url))
        return papers


class OpenAlexSource(PaperSource):
    name = "openalex"
    default_base_url = "https://api.openalex.org/works"

    def _fetch(self, query, limit):
        r = _get(self.base_url, {"search": query, "per_page": limit})
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _abstract(inv: dict | None) -> str:
        if not inv:
            return ""
        positions = [(i, w) for w, idxs in inv.items() for i in idxs]
        positions.sort()
        return " ".join(w for _, w in positions)

    def parse(self, raw: dict) -> list[Paper]:
        papers = []
        for w in raw.get("results", []):
            authors = [a.get("author", {}).get("display_name", "")
                       for a in w.get("authorships", [])]
            venue = (w.get("host_venue") or {}).get("display_name") or \
                    (w.get("primary_location") or {}).get("source", {}).get("display_name")
            papers.append(Paper(
                title=w.get("title") or "", source=self.name, authors=authors,
                year=w.get("publication_year"),
                abstract=self._abstract(w.get("abstract_inverted_index")),
                doi=(w.get("doi") or "").replace("https://doi.org/", "") or None,
                url=w.get("id"), venue=venue, citations=w.get("cited_by_count"),
                external_id=w.get("id")))
        return papers


class SemanticScholarSource(PaperSource):
    name = "semantic_scholar"
    default_base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    _FIELDS = "title,abstract,year,authors,externalIds,url,venue,citationCount"

    def _fetch(self, query, limit):
        r = _get(self.base_url, {"query": query, "limit": limit, "fields": self._FIELDS})
        r.raise_for_status()
        return r.json()

    def parse(self, raw: dict) -> list[Paper]:
        papers = []
        for p in raw.get("data", []):
            authors = [a.get("name", "") for a in p.get("authors", [])]
            doi = (p.get("externalIds") or {}).get("DOI")
            papers.append(Paper(
                title=p.get("title") or "", source=self.name, authors=authors,
                year=p.get("year"), abstract=p.get("abstract") or "",
                doi=doi, url=p.get("url"), venue=p.get("venue"),
                citations=p.get("citationCount"), external_id=p.get("paperId")))
        return papers


class CrossRefSource(PaperSource):
    name = "crossref"
    default_base_url = "https://api.crossref.org/works"

    def _fetch(self, query, limit):
        r = _get(self.base_url, {"query": query, "rows": limit})
        r.raise_for_status()
        return r.json()

    def parse(self, raw: dict) -> list[Paper]:
        papers = []
        for it in raw.get("message", {}).get("items", []):
            title = (it.get("title") or [""])[0]
            authors = [f"{a.get('given', '')} {a.get('family', '')}".strip()
                       for a in it.get("author", [])]
            parts = (it.get("issued", {}).get("date-parts") or [[None]])[0]
            year = parts[0] if parts and isinstance(parts[0], int) else None
            papers.append(Paper(
                title=title, source=self.name, authors=authors, year=year,
                abstract=it.get("abstract", "") or "", doi=it.get("DOI"),
                url=it.get("URL"), venue=(it.get("container-title") or [None])[0],
                citations=it.get("is-referenced-by-count"), external_id=it.get("DOI")))
        return papers


class HALSource(PaperSource):
    name = "hal"
    default_base_url = "https://api.archives-ouvertes.fr/search/"

    def _fetch(self, query, limit):
        r = _get(self.base_url, {
            "q": query, "wt": "json", "rows": limit,
            "fl": "title_s,authFullName_s,abstract_s,doiId_s,uri_s,producedDateY_i"})
        r.raise_for_status()
        return r.json()

    def parse(self, raw: dict) -> list[Paper]:
        papers = []
        for d in raw.get("response", {}).get("docs", []):
            title = d.get("title_s")
            title = title[0] if isinstance(title, list) else (title or "")
            abstract = d.get("abstract_s")
            abstract = abstract[0] if isinstance(abstract, list) else (abstract or "")
            papers.append(Paper(
                title=title, source=self.name,
                authors=d.get("authFullName_s") or [],
                year=d.get("producedDateY_i"), abstract=abstract,
                doi=d.get("doiId_s"), url=d.get("uri_s"), external_id=d.get("uri_s")))
        return papers


SOURCES = {s.name: s for s in [
    ArxivSource, OpenAlexSource, SemanticScholarSource, CrossRefSource, HALSource,
]}
