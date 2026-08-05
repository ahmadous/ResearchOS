"""AI Router — la pièce maîtresse.

Responsabilités :
  1. Agréger les modèles de TOUS les providers configurés (Registry).
  2. Choisir le meilleur modèle pour une requête via une stratégie
     (switch AUTOMATIQUE) — ou respecter un modèle épinglé (switch MANUEL).
  3. Exécuter la complétion avec fallback : si le provider choisi échoue
     (quota, panne), basculer sur le candidat suivant (Observer/telemetry).

Design :
  - `ModelRegistry` : source de vérité des specs + accès aux providers.
  - `AIRouter` : orchestration. Ne connaît que des interfaces.
  - Observers : hooks appelés après chaque appel (coût, latence, tokens) —
    branchés plus tard sur la persistance + WebSocket (Observer Pattern).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Iterator

from .base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    ModelSpec,
    ProviderError,
)
from .factory import ProviderFactory
from .strategies import RoutingContext, RoutingStrategy, get_strategy

log = logging.getLogger("researchos.ai.router")


@dataclass
class ProviderConfig:
    """Config d'un provider actif (vient de la BDD via le LLM Manager)."""
    key: str                       # "openai", "anthropic", ...
    api_key: str | None = None
    base_url: str | None = None
    enabled: bool = True


class ModelRegistry:
    """Catalogue vivant : instancie les providers configurés et indexe leurs modèles."""

    def __init__(self, configs: list[ProviderConfig]):
        self._providers: dict[str, LLMProvider] = {}
        self._specs: dict[str, ModelSpec] = {}          # model_id -> spec
        self._owner: dict[str, str] = {}                # model_id -> provider key
        for cfg in configs:
            if cfg.enabled:
                self.add(cfg)

    def add(self, cfg: ProviderConfig) -> None:
        provider = ProviderFactory.create(cfg.key, cfg.api_key, cfg.base_url)
        self._providers[cfg.key] = provider
        for spec in provider.models():
            self._specs[spec.id] = spec
            self._owner[spec.id] = cfg.key

    def specs(self) -> list[ModelSpec]:
        return list(self._specs.values())

    def spec(self, model_id: str) -> ModelSpec | None:
        return self._specs.get(model_id)

    def provider_for(self, model_id: str) -> LLMProvider:
        key = self._owner.get(model_id)
        if key is None:
            raise ProviderError("registry", f"modèle inconnu: {model_id}")
        return self._providers[key]


# Observer : (response, spec) -> None. Ex: enregistrer coût/tokens, émettre WS.
Observer = Callable[[CompletionResponse, ModelSpec], None]


class AIRouter:
    def __init__(self, registry: ModelRegistry, default_model: str | None = None):
        self.registry = registry
        self.default_model = default_model
        self._observers: list[Observer] = []

    def subscribe(self, observer: Observer) -> None:
        self._observers.append(observer)

    def _notify(self, resp: CompletionResponse, spec: ModelSpec) -> None:
        for obs in self._observers:
            try:
                obs(resp, spec)
            except Exception:            # un observer défaillant ne casse pas l'appel
                log.exception("observer error")

    # --- Sélection ---
    def rank(
        self,
        ctx: RoutingContext,
        strategy: RoutingStrategy | str | None = None,
    ) -> list[ModelSpec]:
        """Renvoie les modèles éligibles triés du meilleur au moins bon."""
        strat = strategy if isinstance(strategy, RoutingStrategy) else get_strategy(strategy)
        eligible = [s for s in self.registry.specs() if strat.eligible(s, ctx)]
        eligible.sort(key=lambda s: strat.score(s, ctx), reverse=True)
        return eligible

    def choose(
        self,
        ctx: RoutingContext,
        strategy: RoutingStrategy | str | None = None,
    ) -> ModelSpec:
        # Switch MANUEL : l'utilisateur a épinglé un modèle -> on le respecte.
        if ctx.pinned_model:
            spec = self.registry.spec(ctx.pinned_model)
            if spec is None:
                raise ProviderError("router", f"modèle épinglé introuvable: {ctx.pinned_model}")
            return spec
        ranked = self.rank(ctx, strategy)
        if not ranked:
            # Filet de sécurité : modèle par défaut si aucun candidat éligible.
            if self.default_model and self.registry.spec(self.default_model):
                return self.registry.spec(self.default_model)
            raise ProviderError("router", "aucun modèle éligible pour cette requête")
        return ranked[0]

    # --- Exécution avec fallback (switch AUTOMATIQUE en cas d'échec) ---
    def complete(
        self,
        request: CompletionRequest,
        ctx: RoutingContext | None = None,
        strategy: RoutingStrategy | str | None = None,
        max_fallbacks: int = 2,
    ) -> CompletionResponse:
        ctx = ctx or RoutingContext()
        candidates = ([self.registry.spec(ctx.pinned_model)] if ctx.pinned_model
                      else self.rank(ctx, strategy))
        candidates = [c for c in candidates if c][: max_fallbacks + 1]
        if not candidates:
            candidates = [self.choose(ctx, strategy)]

        last_err: Exception | None = None
        for spec in candidates:
            provider = self.registry.provider_for(spec.id)
            req = CompletionRequest(**{**request.__dict__, "model": spec.id})
            try:
                resp = provider.complete(req)
                self._notify(resp, spec)
                return resp
            except ProviderError as e:
                last_err = e
                log.warning("provider %s a échoué (%s) — fallback", spec.provider, e)
                if not e.retryable:
                    break
        raise ProviderError("router", f"tous les candidats ont échoué: {last_err}")

    def stream(
        self,
        request: CompletionRequest,
        ctx: RoutingContext | None = None,
        strategy: RoutingStrategy | str | None = None,
    ) -> Iterator[str]:
        ctx = ctx or RoutingContext()
        spec = self.choose(ctx, strategy)
        provider = self.registry.provider_for(spec.id)
        req = CompletionRequest(**{**request.__dict__, "model": spec.id, "stream": True})
        yield from provider.stream(req)
