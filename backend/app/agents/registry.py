"""Registre d'agents — instancie et indexe les agents pour un LLMClient donné.

Permet aussi l'enregistrement à chaud (marketplace / plugins) : `register()`.
"""
from __future__ import annotations

from .base import BaseAgent, LLMClient
from .specialized import all_agent_classes


class AgentRegistry:
    def __init__(self, llm: LLMClient, classes: list[type[BaseAgent]] | None = None):
        self._llm = llm
        self._agents: dict[str, BaseAgent] = {}
        for cls in (classes if classes is not None else all_agent_classes()):
            self.register(cls)

    def register(self, cls: type[BaseAgent]) -> None:
        self._agents[cls.name] = cls(self._llm)

    def has(self, name: str) -> bool:
        return name in self._agents

    def get(self, name: str) -> BaseAgent:
        if name not in self._agents:
            raise KeyError(f"Agent inconnu: {name}")
        return self._agents[name]

    def names(self) -> list[str]:
        return sorted(self._agents)

    def catalog(self) -> list[dict]:
        return [{"name": a.name, "description": a.description,
                 "strategy": a.strategy, "privacy": a.require_privacy}
                for a in sorted(self._agents.values(), key=lambda x: x.name)]
