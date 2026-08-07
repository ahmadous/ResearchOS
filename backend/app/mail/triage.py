"""Tri/priorisation d'emails par le LLM — pur (dépend d'un LLMClient)."""
from __future__ import annotations

import json
import re

from ..agents.base import LLMClient
from ..ai.base import Message

_SYSTEM = (
    "Tu es un assistant qui trie des emails. Pour CHAQUE email numéroté, évalue : "
    "importance (0-100), s'il nécessite une réponse, une catégorie courte, et un "
    "résumé d'une phrase. Réponds UNIQUEMENT par un tableau JSON d'objets "
    '{"n": <num>, "importance": <0-100>, "needs_reply": true/false, '
    '"category": "...", "summary": "..."}. Écris en français.'
)


class MailTriager:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def classify(self, emails: list[dict], pinned_model: str | None = None) -> list[dict]:
        lines = [f"[{i}] De: {e.get('from')} | Sujet: {e.get('subject')} | "
                 f"{(e.get('snippet') or '')[:160]}" for i, e in enumerate(emails, 1)]
        resp = self.llm.complete(
            [Message("system", _SYSTEM), Message("user", "\n".join(lines))],
            strategy="balanced", pinned_model=pinned_model, agent="fact_checker",
            max_tokens=700)
        return self._merge(emails, resp.content)

    @staticmethod
    def _merge(emails: list[dict], raw: str) -> list[dict]:
        arr = []
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if m:
            try:
                arr = json.loads(m.group(0))
            except json.JSONDecodeError:
                arr = []
        by_n = {a.get("n"): a for a in arr if isinstance(a, dict)}
        out = []
        for i, e in enumerate(emails, 1):
            a = by_n.get(i, {})
            try:
                imp = max(0, min(100, int(a.get("importance", 50))))
            except (TypeError, ValueError):
                imp = 50
            out.append({**e,
                        "importance": imp,
                        "needs_reply": bool(a.get("needs_reply", False)),
                        "category": str(a.get("category") or "autre")[:40],
                        "summary": str(a.get("summary") or "")[:200]})
        out.sort(key=lambda x: x["importance"], reverse=True)
        return out
