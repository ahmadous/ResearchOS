"""Génération BibTeX à partir des métadonnées réelles des articles (pur)."""
from __future__ import annotations

import re

_KEYSAFE = re.compile(r"[^a-z0-9]+")


def _cite_key(paper: dict, used: set[str]) -> str:
    authors = paper.get("authors") or []
    first = authors[0].split()[-1].lower() if authors and authors[0].strip() else "anon"
    year = paper.get("year") or "n.d."
    word = ""
    for w in (paper.get("title") or "").split():
        w = _KEYSAFE.sub("", w.lower())
        if len(w) > 3:
            word = w
            break
    key = _KEYSAFE.sub("", f"{first}{year}{word}") or "ref"
    candidate, i = key, 1
    while candidate in used:
        i += 1
        candidate = f"{key}{i}"
    used.add(candidate)
    return candidate


def _escape(v: str) -> str:
    return (v or "").replace("{", "").replace("}", "").strip()


def to_bibtex(papers: list[dict]) -> str:
    used: set[str] = set()
    entries = []
    for p in papers:
        key = _cite_key(p, used)
        fields = {
            "title": _escape(p.get("title", "")),
            "author": " and ".join(_escape(a) for a in (p.get("authors") or []) if a.strip()),
            "year": p.get("year") or "",
            "journal": _escape(p.get("venue") or ""),
            "doi": _escape(p.get("doi") or ""),
            "url": _escape(p.get("url") or ""),
        }
        lines = [f"@article{{{key},"]
        lines += [f"  {k} = {{{v}}}," for k, v in fields.items() if v]
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries)
