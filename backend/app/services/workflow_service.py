"""Service Workflow — CRUD + exécution du DAG d'agents.

L'exécution réutilise l'orchestrateur (Blackboard partagé) : les nœuds tournent
dans l'ordre topologique, chacun voyant les sorties des précédents. La
progression est émise nœud par nœud via le notifier (WebSocket).
"""
from __future__ import annotations

from ..extensions import db
from ..models import Workflow, WorkflowRun
from ..models import workflow_run as WR
from ..realtime import notifier
from ..repositories import WorkflowRepository, WorkflowRunRepository
from ..workflows import topological_order
from ..workflows.graph import WorkflowError
from .agent_service import AgentService
from .llm_service import LLMServiceError


class WorkflowService:
    def __init__(self, agents: AgentService | None = None,
                 repo: WorkflowRepository | None = None,
                 runs: WorkflowRunRepository | None = None):
        self.agents = agents or AgentService()
        self.repo = repo or WorkflowRepository()
        self.runs = runs or WorkflowRunRepository()

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

    # --- Exécutions (runs) : création + contrôle ---
    def create_run(self, user_id: str, wf_id: str) -> dict:
        wf = self.get(user_id, wf_id)
        try:
            order = topological_order(wf.graph)   # valide le graphe tout de suite
        except WorkflowError as e:
            raise LLMServiceError(str(e))
        run = WorkflowRun(user_id=user_id, workflow_id=wf_id, name=wf.name,
                          status=WR.PENDING, total=len(order))
        self.runs.add(run)
        return run.to_dict()

    def _run(self, user_id: str, run_id: str) -> WorkflowRun:
        run = self.runs.get(run_id)
        if not run or run.user_id != user_id:
            raise LLMServiceError("Exécution introuvable")
        return run

    def list_runs(self, user_id: str) -> list[dict]:
        return [r.to_dict() for r in self.runs.for_user(user_id)]

    def get_run(self, user_id: str, run_id: str) -> dict:
        return self._run(user_id, run_id).to_dict(full=True)

    def pause_run(self, user_id: str, run_id: str) -> dict:
        run = self._run(user_id, run_id)
        if run.status == WR.RUNNING:
            run.status = WR.PAUSED
            db.session.commit()
        return run.to_dict()

    def cancel_run(self, user_id: str, run_id: str) -> dict:
        run = self._run(user_id, run_id)
        if run.status in (WR.RUNNING, WR.PAUSED, WR.PENDING):
            run.status = WR.CANCELED
            db.session.commit()
        return run.to_dict()

    # --- Exécution effective (job asynchrone, pausable/reprenable) ---
    def execute_run(self, user_id: str, run_id: str, task_id: str,
                    progress=lambda *_: None) -> dict:
        run = self._run(user_id, run_id)
        wf = self.get(user_id, run.workflow_id)
        order = topological_order(wf.graph)

        orch = self.agents.build_orchestrator(user_id)
        ctx = orch._new_context(goal=wf.name)
        results = list(run.results)
        # Reprise : reconstruit le Blackboard depuis les résultats déjà produits.
        for r in results:
            if r.get("content"):
                ctx.blackboard[r["agent"]] = r["content"]

        # Garde d'entrée : ne pas relancer une exécution mise en pause/annulée.
        if run.status in (WR.PAUSED, WR.CANCELED):
            return run.to_dict(full=True)
        run.status = WR.RUNNING
        db.session.commit()

        for i in range(run.step, len(order)):
            # Contrôle coopératif : on relit le statut en base entre chaque nœud.
            db.session.expire_all()
            run = self._run(user_id, run_id)
            if run.status in (WR.PAUSED, WR.CANCELED):
                run.step = i
                run.results = results
                db.session.commit()
                notifier.task_progress(user_id, task_id, int(i / len(order) * 100),
                                       f"workflow {run.status}")
                return run.to_dict(full=True)

            node = order[i]
            node_id, agent = node["id"], node["agent"]
            task_text = node.get("task") or wf.name
            notifier.workflow_node(user_id, task_id, node_id, "running")
            if orch.registry.has(agent):
                res = orch.registry.get(agent).run(task_text, ctx)
                entry = {"node_id": node_id, "agent": agent, "content": res.content,
                         "model": res.model, "tokens": res.total_tokens}
                notifier.workflow_node(user_id, task_id, node_id, "done", res.content)
            else:
                entry = {"node_id": node_id, "agent": agent, "error": "agent inconnu"}
                notifier.workflow_node(user_id, task_id, node_id, "failed")
            results.append(entry)
            run.step = i + 1
            run.results = results
            db.session.commit()
            progress(int((i + 1) / len(order) * 100), f"{agent} terminé")

        run.status = WR.COMPLETED
        run.results = results
        db.session.commit()
        return run.to_dict(full=True)
