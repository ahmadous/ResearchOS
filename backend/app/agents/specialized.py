"""Agents spécialisés.

La plupart se définissent par un simple prompt système + préférences de routage
(indépendants, extensibles). Certains ont un comportement propre :
  - `PlanningAgent` décompose l'objectif en étapes et les délègue aux autres
    agents (coordination — les agents « communiquent » via le Blackboard).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..ai.base import Message
from .base import AgentContext, AgentResult, BaseAgent


@dataclass(frozen=True)
class AgentSpec:
    name: str
    description: str
    system_prompt: str
    strategy: str = "balanced"
    require_privacy: str | None = None


# --- Catalogue déclaratif des agents « simples » ---
SPECS: list[AgentSpec] = [
    AgentSpec("research", "Synthèse et exploration d'un sujet de recherche",
              "Tu es un agent de recherche. Analyse le sujet, dégage les axes clés, "
              "les concepts et les questions ouvertes, de façon structurée et sourcée.",
              strategy="quality"),
    AgentSpec("web_search", "Formulation de requêtes et synthèse de résultats web",
              "Tu es un agent de recherche web. Produis des requêtes précises puis "
              "synthétise les résultats en citant les sources.", strategy="speed"),
    AgentSpec("pdf", "Analyse et extraction d'informations depuis un document",
              "Tu es un agent d'analyse documentaire. Extrais méthodes, résultats et "
              "limites du texte fourni, sans rien inventer.", strategy="quality"),
    AgentSpec("citation", "Génération et vérification de citations bibliographiques",
              "Tu es un agent de citation. Produis des références correctes (APA/BibTeX) "
              "et associe chaque affirmation à sa source. N'invente jamais de référence.",
              strategy="balanced"),
    AgentSpec("coding", "Écriture et explication de code",
              "Tu es un agent de code. Écris du code correct, commenté et testable, et "
              "explique tes choix.", strategy="quality"),
    AgentSpec("experiment", "Conception de protocoles expérimentaux",
              "Tu es un agent d'expérimentation. Propose un protocole reproductible : "
              "hypothèses, variables, métriques, jeux de données.", strategy="quality"),
    AgentSpec("writing", "Rédaction académique",
              "Tu es un agent de rédaction scientifique. Rédige un texte clair, précis "
              "et rigoureux à partir du contexte fourni par les autres agents.",
              strategy="quality"),
    AgentSpec("reviewer", "Relecture critique (peer review)",
              "Tu es un relecteur. Évalue rigueur, clarté et limites du texte, et liste "
              "des critiques constructives et actionnables.", strategy="quality"),
    AgentSpec("fact_checker", "Vérification factuelle",
              "Tu es un agent de vérification. Repère les affirmations douteuses, indique "
              "leur statut (vérifié/incertain/faux) et ce qu'il faudrait pour confirmer.",
              strategy="quality"),
    AgentSpec("translation", "Traduction préservant le sens technique",
              "Tu es un agent de traduction. Traduis fidèlement en conservant la "
              "terminologie technique.", strategy="cost"),
    AgentSpec("vision", "Description et analyse d'images/figures",
              "Tu es un agent de vision. Décris et interprète les figures/schémas fournis.",
              strategy="quality"),
    AgentSpec("data_analysis", "Analyse de données et statistiques",
              "Tu es un agent d'analyse de données. Décris les tendances, corrélations et "
              "tests pertinents à partir des données fournies.", strategy="quality"),
    AgentSpec("graph", "Extraction d'entités et relations (knowledge graph)",
              "Tu es un agent de graphe de connaissances. Extrais entités (auteurs, "
              "institutions, algorithmes, datasets) et leurs relations.", strategy="balanced"),
    AgentSpec("summarizer", "Résumé concis et fidèle",
              "Tu es un agent de résumé. Produis un résumé fidèle, hiérarchisé et concis.",
              strategy="cost"),
]


def _make_agent(spec: AgentSpec) -> type[BaseAgent]:
    """Fabrique une classe d'agent à partir d'une spec déclarative."""
    return type(f"{spec.name.title()}Agent", (BaseAgent,), {
        "name": spec.name, "description": spec.description,
        "system_prompt": spec.system_prompt, "strategy": spec.strategy,
        "require_privacy": spec.require_privacy,
    })


class PlanningAgent(BaseAgent):
    """Décompose l'objectif en un plan d'étapes déléguées aux autres agents."""

    name = "planning"
    description = "Décompose un objectif de recherche en étapes et délègue aux agents"
    strategy = "quality"

    @property
    def system_prompt(self) -> str:  # type: ignore[override]
        return (
            "Tu es un agent de planification. Décompose l'objectif en 2 à 5 étapes. "
            "Réponds UNIQUEMENT par un tableau JSON d'objets "
            '{\"agent\": <nom>, \"task\": <consigne précise>}. '
            "N'utilise que des agents de la liste fournie."
        )

    def build_messages(self, task, context):
        agents = ", ".join(a for a in context.available_agents if a != self.name)
        msgs = super().build_messages(task, context)
        msgs.insert(1, Message("system", f"Agents disponibles : {agents}"))
        return msgs

    def postprocess(self, result: AgentResult, context: AgentContext) -> AgentResult:
        result.data["plan"] = self._parse_plan(result.content, context.available_agents)
        return result

    @staticmethod
    def _parse_plan(text: str, available: list[str]) -> list[dict]:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if not m:
            return []
        try:
            raw = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
        plan = []
        for step in raw:
            if isinstance(step, dict) and step.get("agent") in available and step.get("task"):
                plan.append({"agent": step["agent"], "task": step["task"]})
        return plan


def all_agent_classes() -> list[type[BaseAgent]]:
    # Les agents outillés (vraie recherche, RAG, KG) remplacent les versions LLM
    # génériques du même nom ; le reste garde le comportement LLM déclaratif.
    from .tool_agents import TOOL_AGENTS
    tool_names = {c.name for c in TOOL_AGENTS}
    generic = [_make_agent(s) for s in SPECS if s.name not in tool_names]
    return [PlanningAgent, *TOOL_AGENTS, *generic]
