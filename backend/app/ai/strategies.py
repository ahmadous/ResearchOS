"""Stratégies de sélection de modèle (Strategy Pattern).

Le routeur ne code EN DUR aucune règle de choix. Il reçoit une stratégie
(coût / vitesse / qualité / confidentialité / équilibré) et lui délègue le
scoring des modèles candidats. Ajouter une politique = ajouter une classe.

Chaque stratégie renvoie un score 0..1 pour un `ModelSpec` donné, en tenant
compte des contraintes de la requête (`RoutingContext`).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field

from .base import Modality, ModelSpec, Privacy


@dataclass
class RoutingContext:
    """Contraintes et signaux fournis par l'appelant pour guider le routage."""
    required_modality: Modality = Modality.TEXT
    min_context: int = 0                 # tokens d'entrée estimés à absorber
    needs_tools: bool = False
    require_privacy: Privacy | None = None   # ex: LOCAL pour données sensibles
    max_cost_per_1m: float | None = None     # plafond de coût input
    allowed_providers: set[str] | None = None
    pinned_model: str | None = None          # switch MANUEL : force ce modèle
    hints: dict = field(default_factory=dict)


class RoutingStrategy(abc.ABC):
    name: str = "base"

    def eligible(self, spec: ModelSpec, ctx: RoutingContext) -> bool:
        """Filtre dur : élimine les modèles qui ne peuvent PAS traiter la requête."""
        if not spec.supports(ctx.required_modality):
            return False
        if ctx.needs_tools and not spec.supports_tools:
            return False
        if ctx.min_context and spec.context_window < ctx.min_context:
            return False
        if ctx.require_privacy and spec.privacy != ctx.require_privacy:
            return False
        if ctx.max_cost_per_1m is not None and spec.input_cost > ctx.max_cost_per_1m:
            return False
        if ctx.allowed_providers and spec.provider not in ctx.allowed_providers:
            return False
        return True

    @abc.abstractmethod
    def score(self, spec: ModelSpec, ctx: RoutingContext) -> float:
        """Score 0..1 parmi les modèles éligibles (plus haut = meilleur)."""


def _cost_score(spec: ModelSpec) -> float:
    """Normalise le coût en score (moins cher => proche de 1). Réf. haute = 100 USD/1M."""
    blended = (spec.input_cost + spec.output_cost) / 2
    return max(0.0, 1.0 - min(blended, 100.0) / 100.0)


class CostStrategy(RoutingStrategy):
    name = "cost"

    def score(self, spec, ctx):
        return _cost_score(spec)


class SpeedStrategy(RoutingStrategy):
    name = "speed"

    def score(self, spec, ctx):
        return spec.speed


class QualityStrategy(RoutingStrategy):
    name = "quality"

    def score(self, spec, ctx):
        return spec.quality


class PrivacyStrategy(RoutingStrategy):
    name = "privacy"

    def score(self, spec, ctx):
        # Local > cloud privé > cloud. La qualité départage à confidentialité égale.
        rank = {Privacy.LOCAL: 1.0, Privacy.PRIVATE_CLOUD: 0.6, Privacy.CLOUD: 0.2}
        return 0.7 * rank[spec.privacy] + 0.3 * spec.quality


class BalancedStrategy(RoutingStrategy):
    """Compromis pondéré — la politique par défaut de la plateforme."""
    name = "balanced"

    def __init__(self, w_quality=0.45, w_cost=0.35, w_speed=0.20):
        self.w_quality, self.w_cost, self.w_speed = w_quality, w_cost, w_speed

    def score(self, spec, ctx):
        return (self.w_quality * spec.quality
                + self.w_cost * _cost_score(spec)
                + self.w_speed * spec.speed)


STRATEGIES: dict[str, RoutingStrategy] = {
    s.name: s for s in (
        CostStrategy(), SpeedStrategy(), QualityStrategy(),
        PrivacyStrategy(), BalancedStrategy(),
    )
}


def get_strategy(name: str | None) -> RoutingStrategy:
    return STRATEGIES.get(name or "balanced", STRATEGIES["balanced"])
