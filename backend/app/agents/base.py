"""Noyau des agents — indépendant de Flask et de la base de données.

Un agent dépend UNIQUEMENT de l'interface `LLMClient` (pas du routeur concret).
Ça les rend testables sans réseau et interchangeables. La communication
inter-agents passe par un `AgentContext` partagé (pattern Blackboard) : chaque
agent y publie son résultat et peut invoquer un pair via `context.call(...)`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol

from ..ai.base import Message


@dataclass
class AgentLLMResponse:
    content: str
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class LLMClient(Protocol):
    """Contrat minimal dont un agent a besoin pour raisonner."""

    def complete(
        self,
        messages: list[Message],
        *,
        strategy: str = "balanced",
        require_privacy: str | None = None,
        pinned_model: str | None = None,
        agent: str | None = None,
    ) -> AgentLLMResponse: ...


@dataclass
class AgentResult:
    agent: str
    content: str
    model: str = ""
    provider: str = ""
    cost_usd: float = 0.0
    total_tokens: int = 0
    data: dict = field(default_factory=dict)   # sorties structurées (plan, citations…)


# Dispatcher injecté par l'orchestrateur : (agent_name, task, context) -> AgentResult
Dispatch = Callable[[str, str, "AgentContext"], AgentResult]


@dataclass
class AgentContext:
    """État partagé entre agents (Blackboard) + outils réels + appel de pairs."""
    goal: str
    blackboard: dict[str, str] = field(default_factory=dict)   # agent -> dernière sortie (texte)
    data: dict = field(default_factory=dict)                   # données structurées partagées
    tools: dict = field(default_factory=dict)                  # outils réels (scholar, rag, kg…)
    history: list[Message] = field(default_factory=list)
    available_agents: list[str] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)            # journal d'exécution
    _dispatch: Dispatch | None = None

    def call(self, agent_name: str, task: str) -> AgentResult:
        """Un agent délègue une sous-tâche à un autre agent."""
        if self._dispatch is None:
            raise RuntimeError("AgentContext non relié à un orchestrateur")
        return self._dispatch(agent_name, task, self)

    def use_tool(self, name: str, *args, **kwargs):
        """Appelle un outil réel s'il est disponible, sinon renvoie None."""
        fn = self.tools.get(name)
        return fn(*args, **kwargs) if fn else None


class BaseAgent:
    """Agent générique (Template Method).

    Sous-classer = surcharger `name`, `description`, `system_prompt` et,
    au besoin, `preprocess`/`postprocess`. La mécanique d'appel LLM est fixe.
    """

    name: str = "base"
    description: str = ""
    system_prompt: str = "Tu es un assistant de recherche rigoureux."
    strategy: str = "balanced"          # stratégie de routage préférée
    require_privacy: str | None = None  # ex: "local" pour un agent sensible

    def __init__(self, llm: LLMClient):
        self.llm = llm

    # --- points d'extension ---
    def preprocess(self, task: str, context: AgentContext) -> str:
        """Peut enrichir la tâche (ex: injecter des documents). Défaut: identité."""
        return task

    def postprocess(self, result: AgentResult, context: AgentContext) -> AgentResult:
        return result

    # --- squelette figé ---
    def build_messages(self, task: str, context: AgentContext) -> list[Message]:
        msgs = [Message("system", self.system_prompt)]
        if context.blackboard:
            shared = "\n\n".join(f"### {a}\n{txt[:1500]}"
                                 for a, txt in context.blackboard.items())
            msgs.append(Message("system", f"Contexte produit par les autres agents :\n{shared}"))
        msgs.append(Message("user", task))
        return msgs

    def run(self, task: str, context: AgentContext) -> AgentResult:
        task = self.preprocess(task, context)
        messages = self.build_messages(task, context)
        resp = self.llm.complete(
            messages, strategy=self.strategy,
            require_privacy=self.require_privacy, agent=self.name,
        )
        result = AgentResult(
            agent=self.name, content=resp.content,
            model=resp.model, provider=resp.provider,
            cost_usd=resp.cost_usd,
            total_tokens=resp.prompt_tokens + resp.completion_tokens,
        )
        context.blackboard[self.name] = result.content
        context.trace.append({"agent": self.name, "model": resp.model,
                              "tokens": result.total_tokens})
        return self.postprocess(result, context)
