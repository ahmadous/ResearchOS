"""Extraction d'un graphe de connaissances depuis du texte.

Pur : dépend d'un `LLMClient`. On demande au modèle un JSON strict et on le
parse de façon défensive (le modèle peut ajouter du texte autour).
"""
from __future__ import annotations

import json
import re

from ..agents.base import LLMClient
from ..ai.base import Message

ENTITY_TYPES = ("author", "institution", "dataset", "algorithm", "method", "concept")

_SYSTEM = (
    "Tu extrais un graphe de connaissances d'un texte scientifique. "
    "Réponds UNIQUEMENT par un objet JSON de la forme "
    '{"entities":[{"name":"...","type":"author|institution|dataset|algorithm|method|concept"}],'
    '"relations":[{"source":"...","target":"...","label":"..."}]}. '
    "source/target doivent être des noms d'entités. Pas de texte hors du JSON."
)


class KGExtractor:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(self, text: str) -> dict:
        messages = [Message("system", _SYSTEM),
                    Message("user", f"Texte :\n{text[:6000]}")]
        resp = self.llm.complete(messages, strategy="quality", agent="graph")
        return self._parse(resp.content)

    @staticmethod
    def _parse(raw: str) -> dict:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"entities": [], "relations": []}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"entities": [], "relations": []}

        entities, seen = [], set()
        for e in data.get("entities", []):
            name = (e.get("name") or "").strip()
            if not name:
                continue
            etype = e.get("type") if e.get("type") in ENTITY_TYPES else "concept"
            key = (name.lower(), etype)
            if key not in seen:
                seen.add(key)
                entities.append({"name": name, "type": etype})

        names = {e["name"].lower() for e in entities}
        relations = []
        for r in data.get("relations", []):
            s = (r.get("source") or "").strip()
            t = (r.get("target") or "").strip()
            if not s or not t or s.lower() == t.lower():
                continue
            # Les entités citées uniquement dans une relation deviennent des concepts.
            for n in (s, t):
                if n.lower() not in names:
                    names.add(n.lower())
                    entities.append({"name": n, "type": "concept"})
            relations.append({"source": s, "target": t,
                              "label": (r.get("label") or "lié à").strip()[:80]})
        return {"entities": entities, "relations": relations}
