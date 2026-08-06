"""Utilitaires de graphe pour les workflows : validation + tri topologique.

Le graphe doit être un DAG (pas de cycle). Le tri topologique (Kahn) donne un
ordre d'exécution où chaque nœud passe après tous ses prédécesseurs.
"""
from __future__ import annotations

from collections import deque


class WorkflowError(Exception):
    pass


def validate(graph: dict) -> tuple[list[dict], list[dict]]:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        raise WorkflowError("Le workflow ne contient aucun nœud")
    ids = [n.get("id") for n in nodes]
    if len(set(ids)) != len(ids) or None in ids:
        raise WorkflowError("Identifiants de nœuds invalides ou dupliqués")
    idset = set(ids)
    for n in nodes:
        if not n.get("agent"):
            raise WorkflowError(f"Nœud {n.get('id')} sans agent")
    for e in edges:
        if e.get("source") not in idset or e.get("target") not in idset:
            raise WorkflowError("Arête référençant un nœud inexistant")
    return nodes, edges


def topological_order(graph: dict) -> list[dict]:
    """Renvoie les nœuds dans un ordre d'exécution valide. Lève si cycle."""
    nodes, edges = validate(graph)
    by_id = {n["id"]: n for n in nodes}
    indeg = {n["id"]: 0 for n in nodes}
    succ: dict[str, list[str]] = {n["id"]: [] for n in nodes}
    for e in edges:
        succ[e["source"]].append(e["target"])
        indeg[e["target"]] += 1

    # File des nœuds sans dépendance ; ordre stable par position d'insertion.
    queue = deque([nid for nid in indeg if indeg[nid] == 0])
    order: list[dict] = []
    while queue:
        nid = queue.popleft()
        order.append(by_id[nid])
        for m in succ[nid]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)

    if len(order) != len(nodes):
        raise WorkflowError("Cycle détecté : le workflow doit être un graphe acyclique")
    return order
