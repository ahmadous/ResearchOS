"""Orchestrateur — coordonne les agents.

Trois modes :
  - `run`      : exécute un agent unique.
  - `pipeline` : chaîne d'agents partageant le même contexte (le suivant voit les
                 sorties des précédents via le Blackboard).
  - `auto`     : le PlanningAgent décompose l'objectif puis délègue aux agents
                 désignés — illustration de la communication inter-agents.
"""
from __future__ import annotations

from .base import AgentContext, AgentResult
from .registry import AgentRegistry


class Orchestrator:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def _new_context(self, goal: str) -> AgentContext:
        return AgentContext(
            goal=goal,
            available_agents=self.registry.names(),
            _dispatch=self._dispatch,
        )

    def _dispatch(self, agent_name: str, task: str, context: AgentContext) -> AgentResult:
        return self.registry.get(agent_name).run(task, context)

    # --- Modes ---
    def run(self, agent_name: str, task: str, *, goal: str | None = None) -> AgentResult:
        if not self.registry.has(agent_name):
            raise KeyError(f"Agent inconnu: {agent_name}")
        ctx = self._new_context(goal or task)
        return self.registry.get(agent_name).run(task, ctx)

    def pipeline(self, steps: list[dict], *, goal: str) -> dict:
        """steps = [{"agent": name, "task": consigne}, ...] exécutés en séquence."""
        ctx = self._new_context(goal)
        results = []
        for step in steps:
            agent, task = step["agent"], step["task"]
            if not self.registry.has(agent):
                raise KeyError(f"Agent inconnu: {agent}")
            results.append(self._as_dict(self.registry.get(agent).run(task, ctx)))
        return {"goal": goal, "results": results, "trace": ctx.trace}

    def auto(self, goal: str, *, max_steps: int = 5) -> dict:
        """Planning décompose l'objectif puis les agents désignés collaborent."""
        ctx = self._new_context(goal)
        plan_result = self.registry.get("planning").run(goal, ctx)
        plan = plan_result.data.get("plan", [])
        results = [self._as_dict(plan_result)]
        for step in plan[:max_steps]:
            if self.registry.has(step["agent"]):
                results.append(self._as_dict(ctx.call(step["agent"], step["task"])))
        # Synthèse finale si un rédacteur est disponible et pas déjà utilisé.
        return {"goal": goal, "plan": plan, "results": results, "trace": ctx.trace}

    @staticmethod
    def _as_dict(r: AgentResult) -> dict:
        return {"agent": r.agent, "content": r.content, "model": r.model,
                "provider": r.provider, "cost_usd": round(r.cost_usd, 6),
                "total_tokens": r.total_tokens, "data": r.data}
