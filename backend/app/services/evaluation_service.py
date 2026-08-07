"""Service d'évaluation — relie l'Evaluator au routeur IA de l'utilisateur."""
from __future__ import annotations

from ..evaluation import Evaluator
from .agent_service import RouterLLMClient
from .llm_service import LLMService, LLMServiceError


class EvaluationService:
    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def evaluate(self, user_id: str, question: str, answer: str,
                 context: str = "", pinned_model: str | None = None) -> dict:
        if not answer.strip():
            raise LLMServiceError("Rien à évaluer (réponse vide)")
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError("Aucun modèle disponible pour l'évaluation")
        evaluator = Evaluator(RouterLLMClient(user_id, self.llm_service))
        return evaluator.evaluate(question, answer, context, pinned_model)
