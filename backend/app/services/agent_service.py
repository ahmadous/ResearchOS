"""Service Agents — relie le package `agents` (pur) au routeur IA et à la BDD.

`RouterLLMClient` adapte l'`AIRouter` à l'interface `LLMClient` attendue par les
agents, et journalise la consommation par agent (colonne ModelUsage.agent).
Les agents restent donc totalement découplés de Flask/SQLAlchemy.
"""
from __future__ import annotations

from ..agents import AgentLLMResponse, AgentRegistry, Orchestrator
from ..ai import CompletionRequest, Message
from ..ai.strategies import Privacy, RoutingContext
from ..models import ModelUsage
from ..repositories import UsageRepository
from .llm_service import LLMService, LLMServiceError


class RouterLLMClient:
    """Adaptateur AIRouter -> LLMClient (avec télémétrie par agent)."""

    def __init__(self, user_id: str, llm_service: LLMService,
                 usage: UsageRepository | None = None):
        self.user_id = user_id
        self.router = llm_service.router_for(user_id, record_usage=False)
        self.usage = usage or UsageRepository()

    def complete(self, messages, *, strategy="balanced", require_privacy=None,
                 pinned_model=None, agent=None, max_tokens=None) -> AgentLLMResponse:
        ctx = RoutingContext(
            pinned_model=pinned_model,
            require_privacy=Privacy(require_privacy) if require_privacy else None,
        )
        req = CompletionRequest(
            messages=[Message(role=m.role, content=m.content) for m in messages],
            max_tokens=max_tokens)
        resp = self.router.complete(req, ctx=ctx, strategy=strategy)
        # Télémétrie taguée avec l'agent appelant.
        self.usage.add(ModelUsage(
            user_id=self.user_id, provider=resp.provider, model=resp.model,
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            cost_usd=resp.cost_usd, latency_ms=resp.latency_ms, agent=agent,
        ))
        return AgentLLMResponse(
            content=resp.content, model=resp.model, provider=resp.provider,
            prompt_tokens=resp.usage.prompt_tokens,
            completion_tokens=resp.usage.completion_tokens,
            cost_usd=resp.cost_usd, latency_ms=resp.latency_ms,
        )


class AgentService:
    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()

    def _tools(self, user_id: str) -> dict:
        """Vrais outils liés à l'utilisateur, injectés dans les agents."""
        def scholar_search(query, limit=6):
            from .scholar_service import ScholarService
            return ScholarService().search(query, None, limit)["results"][:limit]

        def rag_context(query, k=4):
            from ..rag import get_embedder, hybrid_search
            from ..repositories import ChunkRepository
            recs = ChunkRepository().records_for_user(user_id)
            if not recs:
                return ""
            from flask import current_app
            emb = get_embedder(current_app.config.get("EMBEDDING_BACKEND", "hashing"),
                               base_url=current_app.config.get("OLLAMA_URL", ""))
            hits = hybrid_search(query, emb.embed(query), recs, k=k)
            return "\n\n".join(h.record["text"] for h in hits)

        def kg_extract(text):
            from .knowledge_service import KnowledgeGraphService
            return KnowledgeGraphService().extract_and_merge(user_id, text=text)

        return {"scholar_search": scholar_search, "rag_context": rag_context,
                "kg_extract": kg_extract}

    def _orchestrator(self, user_id: str) -> Orchestrator:
        registry = AgentRegistry(RouterLLMClient(user_id, self.llm_service))
        return Orchestrator(registry, tools=self._tools(user_id))

    def build_orchestrator(self, user_id: str) -> Orchestrator:
        """Orchestrateur prêt à l'emploi (utilisé par le moteur de workflows)."""
        return self._orchestrator(user_id)

    def _guard_models(self, user_id: str) -> None:
        if not self.llm_service.router_for(user_id, record_usage=False).registry.specs():
            raise LLMServiceError(
                "Aucun modèle disponible pour les agents. Configurez un fournisseur "
                "ou démarrez Ollama (ex: `ollama pull llama3.2`).")

    # --- Use-cases ---
    def list_agents(self, user_id: str) -> list[dict]:
        return AgentRegistry(RouterLLMClient(user_id, self.llm_service)).catalog()

    def run(self, user_id: str, agent: str, task: str, goal: str | None = None) -> dict:
        self._guard_models(user_id)
        orch = self._orchestrator(user_id)
        if not orch.registry.has(agent):
            raise LLMServiceError(f"Agent inconnu: {agent}")
        return orch._as_dict(orch.run(agent, task, goal=goal))

    def stream(self, user_id: str, agent: str, task: str,
               pinned_model: str | None = None):
        """Streaming d'un agent : construit son prompt puis diffuse les tokens.

        L'utilisateur peut imposer un modèle rapide (ex: llama3.2:1b) au lieu de
        subir la stratégie « quality » de l'agent (qui vise le plus gros modèle).
        """
        self._guard_models(user_id)
        orch = self._orchestrator(user_id)
        if not orch.registry.has(agent):
            raise LLMServiceError(f"Agent inconnu: {agent}")
        ag = orch.registry.get(agent)
        ctx = orch._new_context(goal=task)
        task = ag.preprocess(task, ctx)             # déclenche les vrais outils (scholar/RAG/KG)
        messages = ag.build_messages(task, ctx)     # system + contexte + tâche
        router = self.llm_service.router_for(user_id, record_usage=False)
        rctx = RoutingContext(pinned_model=pinned_model)
        chosen = router.choose(rctx, ag.strategy)
        req = CompletionRequest(messages=messages, max_tokens=512)
        return chosen, router.stream(req, ctx=rctx, strategy=ag.strategy)

    def pipeline(self, user_id: str, steps: list[dict], goal: str) -> dict:
        self._guard_models(user_id)
        try:
            return self._orchestrator(user_id).pipeline(steps, goal=goal)
        except KeyError as e:
            raise LLMServiceError(str(e))

    def auto(self, user_id: str, goal: str, max_steps: int = 5) -> dict:
        self._guard_models(user_id)
        return self._orchestrator(user_id).auto(goal, max_steps=max_steps)
