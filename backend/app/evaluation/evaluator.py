"""Évaluation critique d'une réponse (fact-check + score de confiance).

Pur : dépend d'un `LLMClient`. Demande un JSON strict et le parse défensivement.
Un second modèle relit la réponse : hallucinations, fiabilité, corrections.
"""
from __future__ import annotations

import json
import re

from ..agents.base import LLMClient
from ..ai.base import Message

VERDICTS = ("reliable", "uncertain", "unreliable")

_SYSTEM = (
    "Tu es un évaluateur critique et rigoureux. On te donne une question et une "
    "réponse. Évalue la fiabilité de la réponse : repère les affirmations "
    "douteuses ou inventées (hallucinations), juge la qualité, propose une "
    "correction si nécessaire. Réponds UNIQUEMENT par un objet JSON : "
    '{"confidence": <0-100>, "verdict": "reliable|uncertain|unreliable", '
    '"issues": ["..."], "correction": "..."}. Écris en français.'
)


class Evaluator:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def evaluate(self, question: str, answer: str, context: str = "",
                 pinned_model: str | None = None) -> dict:
        user = f"Question :\n{question}\n\nRéponse à évaluer :\n{answer}"
        if context:
            user += f"\n\nContexte de référence :\n{context[:3000]}"
        resp = self.llm.complete(
            [Message("system", _SYSTEM), Message("user", user)],
            strategy="balanced", pinned_model=pinned_model, agent="fact_checker")
        return self._parse(resp.content)

    @staticmethod
    def _parse(raw: str) -> dict:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = {}
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = {}
        # Normalisation défensive.
        try:
            conf = int(data.get("confidence", 50))
        except (TypeError, ValueError):
            conf = 50
        conf = max(0, min(100, conf))
        verdict = data.get("verdict")
        if verdict not in VERDICTS:
            verdict = "reliable" if conf >= 70 else "uncertain" if conf >= 40 else "unreliable"
        issues = data.get("issues") or []
        if not isinstance(issues, list):
            issues = [str(issues)]
        issues = [str(i) for i in issues][:8]
        correction = str(data.get("correction") or "")[:1500]
        return {"confidence": conf, "verdict": verdict,
                "issues": issues, "correction": correction}
