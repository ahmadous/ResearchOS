"""Service Workflow — CRUD + exécution du DAG d'agents.

L'exécution réutilise l'orchestrateur (Blackboard partagé) : les nœuds tournent
dans l'ordre topologique, chacun voyant les sorties des précédents. La
progression est émise nœud par nœud via le notifier (WebSocket).
"""
from __future__ import annotations

from ..models import Workflow
from ..realtime import notifier
from ..repositories import WorkflowRepository
from ..workflows import topological_order
from ..workflows.graph import WorkflowError
from .agent_service import AgentService
from .llm_service import LLMServiceError


class WorkflowService:
    def __init__(self, agents: AgentService | None = None,
                 repo: WorkflowRepository | None = None):
        self.agents = agents or AgentService()
        self.repo = repo or WorkflowRepository()

    # --- CRUD ---
    def create(self, user_id: str, name: str, graph: dict | None = None) -> dict:
        wf = Workflow(user_id=user_id, name=name or "Nouveau workflow")
        wf.graph = graph or {"nodes": [], "edges": []}
        self.repo.add(wf)
        return wf.to_dict()

    def list(self, user_id: str) -> list[dict]:
        return [w.to_dict() for w in self.repo.for_user(user_id)]

    def get(self, user_id: str, wf_id: str) -> Workflow:
        wf = self.repo.get(wf_id)
        if not wf or wf.user_id != user_id:
            raise LLMServiceError("Workflow introuvable")
        return wf

    def update(self, user_id: str, wf_id: str, *, name: str | None = None,
               graph: dict | None = None) -> dict:
        wf = self.get(user_id, wf_id)
        if name is not None:
            wf.name = name
        if graph is not None:
            wf.graph = graph
        self.repo.commit()
        return wf.to_dict()

    def delete(self, user_id: str, wf_id: str) -> None:
        self.repo.delete(self.get(user_id, wf_id))

    # --- Exécution (appelée par le job asynchrone) ---
    def execute(self, user_id: str, wf_id: str, task_id: str,
                progress=lambda *_: None, inputs: dict | None = None) -> dict:
        wf = self.get(user_id, wf_id)
        try:
            order = topological_order(wf.graph)
        except WorkflowError as e:
            raise LLMServiceError(str(e))

        orch = self.agents.build_orchestrator(user_id)
        if not orch.registry:  # pragma: no cover
            raise LLMServiceError("Aucun agent disponible")
        ctx = orch._new_context(goal=wf.name)
        results = []
        total = len(order)
        for i, node in enumerate(order):
            node_id, agent = node["id"], node["agent"]
            task_text = node.get("task") or (inputs or {}).get(node_id) or wf.name
            if not orch.registry.has(agent):
                notifier.workflow_node(user_id, task_id, node_id, "failed")
                results.append({"node_id": node_id, "agent": agent, "error": "agent inconnu"})
                continue
            notifier.workflow_node(user_id, task_id, node_id, "running")
            res = orch.registry.get(agent).run(task_text, ctx)
            notifier.workflow_node(user_id, task_id, node_id, "done", res.content)
            results.append({"node_id": node_id, "agent": agent,
                            "content": res.content, "model": res.model,
                            "tokens": res.total_tokens})
            progress(int((i + 1) / total * 100), f"{agent} terminé")
        return {"workflow_id": wf_id, "name": wf.name, "results": results}
