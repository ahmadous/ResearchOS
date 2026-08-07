"""Service LLM — pont entre la couche IA (routeur) et la persistance.

Responsabilités :
  - construire un `AIRouter` à partir des credentials d'un utilisateur ;
  - brancher un Observer qui journalise chaque appel dans `ModelUsage` ;
  - exposer les use-cases du LLM Manager : lister modèles, tester, compléter,
    gérer les providers, consulter la consommation.
"""
from __future__ import annotations

from ..ai import (
    AIRouter,
    CompletionRequest,
    Message,
    ModelRegistry,
    ProviderConfig,
    ProviderFactory,
    ProviderError,
)
from ..ai.base import Modality, Privacy
from ..ai.strategies import RoutingContext
from ..models import ModelUsage, ProviderCredential
from ..repositories import ProviderRepository, UsageRepository


class LLMServiceError(Exception):
    status_code = 400


# Consigne système du chat (la langue est gérée par language_directive).
CHAT_SYSTEM = (
    "Tu es l'assistant de ResearchOS. Sois clair et concis, sauf si l'utilisateur "
    "demande explicitement plus de détails."
)
# Longueur max par défaut d'une réponse de chat (borne le temps de génération).
CHAT_MAX_TOKENS = 384


from ..language import detect_language as _detect_language  # noqa: E402 (ré-export tests)
from ..language import language_directive


def _with_system(messages: list[dict]) -> list[dict]:
    if any(m.get("role") == "system" for m in messages):
        return messages
    last_user = next((m["content"] for m in reversed(messages)
                      if m.get("role") == "user"), "")
    system = CHAT_SYSTEM + language_directive(last_user)
    return [{"role": "system", "content": system}, *messages]


class LLMService:
    def __init__(self, providers: ProviderRepository | None = None,
                 usage: UsageRepository | None = None):
        self.providers = providers or ProviderRepository()
        self.usage = usage or UsageRepository()

    # --- Construction du routeur pour un utilisateur ---
    def _configs(self, user_id: str) -> list[ProviderConfig]:
        """Providers de l'utilisateur + Ollama TOUJOURS présent comme socle local.

        Aucun fournisseur cloud n'est requis : si l'utilisateur n'a rien
        configuré (ou si ses clés cloud sont indisponibles), on bascule
        automatiquement sur Ollama et ses modèles installés localement.
        """
        from flask import current_app
        creds = self.providers.enabled_for_user(user_id)
        configs = [ProviderConfig(key=c.provider_key, api_key=c.api_key,
                                  base_url=c.base_url) for c in creds]
        # Injecte le socle Ollama sauf si l'utilisateur a déjà défini son propre Ollama.
        if not any(c.key == "ollama" for c in configs):
            configs.append(ProviderConfig(
                key="ollama",
                base_url=current_app.config.get("OLLAMA_URL", "http://localhost:11434"),
            ))
        return configs

    def router_for(self, user_id: str, *, record_usage: bool = True,
                   agent: str | None = None) -> AIRouter:
        configs = self._configs(user_id)  # jamais vide : Ollama est toujours là
        registry = ModelRegistry(configs)
        router = AIRouter(registry)

        # Observer : persiste la télémétrie à chaque appel (Observer Pattern).
        # Désactivable pour les agents, qui enregistrent eux-mêmes (tag agent).
        if record_usage:
            def _record(resp, spec):
                self.usage.add(ModelUsage(
                    user_id=user_id, provider=resp.provider, model=resp.model,
                    prompt_tokens=resp.usage.prompt_tokens,
                    completion_tokens=resp.usage.completion_tokens,
                    cost_usd=resp.cost_usd, latency_ms=resp.latency_ms, agent=agent,
                ))
            router.subscribe(_record)
        return router

    # --- LLM Manager : catalogue ---
    def catalog(self, user_id: str) -> list[dict]:
        """Tous les modèles disponibles pour l'utilisateur + métadonnées de routing."""
        try:
            registry = ModelRegistry(self._configs(user_id))
        except LLMServiceError:
            return []
        return [self._spec_dict(s) for s in registry.specs()]

    @staticmethod
    def _spec_dict(s) -> dict:
        return {
            "id": s.id, "provider": s.provider, "display_name": s.display_name,
            "context_window": s.context_window, "max_output": s.max_output,
            "input_cost": s.input_cost, "output_cost": s.output_cost,
            "speed": s.speed, "quality": s.quality, "privacy": s.privacy.value,
            "supports_tools": s.supports_tools,
            "modalities": [m.value for m in s.modalities],
        }

    def available_providers(self) -> list[str]:
        return ProviderFactory.available()

    def ollama_status(self, user_id: str | None = None) -> dict:
        """État du démon Ollama local + modèles réellement installés sur la machine.

        Si l'utilisateur a configuré son propre Ollama (ex: distant), on cible son
        URL ; sinon l'URL locale par défaut.
        """
        from flask import current_app
        base_url = current_app.config.get("OLLAMA_URL", "http://localhost:11434")
        if user_id:
            own = next((c for c in self.providers.enabled_for_user(user_id)
                        if c.provider_key == "ollama" and c.base_url), None)
            if own:
                base_url = own.base_url
        provider = ProviderFactory.create("ollama", base_url=base_url)
        up = provider.is_up()
        models = [self._spec_dict(s) for s in provider.models()] if up else []
        return {"up": up, "base_url": base_url, "count": len(models),
                "models": models,
                "hint": None if up else
                "Démon Ollama injoignable. Lancez `ollama serve`, puis installez "
                "un modèle avec `ollama pull llama3.2`."}

    # --- LLM Manager : gestion des providers ---
    def add_provider(self, user_id: str, provider_key: str, api_key: str = "",
                     base_url: str | None = None, label: str = "default",
                     is_default: bool = False) -> dict:
        if provider_key not in ProviderFactory.available():
            raise LLMServiceError(f"Fournisseur inconnu: {provider_key}")
        from ..security import encrypt
        if is_default:
            for c in self.providers.for_user(user_id):
                c.is_default = False
        cred = ProviderCredential(
            user_id=user_id, provider_key=provider_key, label=label,
            api_key_encrypted=encrypt(api_key) if api_key else "",
            base_url=base_url, is_default=is_default,
        )
        self.providers.add(cred)
        return cred.to_dict()

    def list_providers(self, user_id: str) -> list[dict]:
        return [c.to_dict() for c in self.providers.for_user(user_id)]

    def delete_provider(self, user_id: str, cred_id: str) -> None:
        cred = self.providers.get(cred_id)
        if not cred or cred.user_id != user_id:
            raise LLMServiceError("Fournisseur introuvable")
        self.providers.delete(cred)

    # --- LLM Manager : test d'un modèle ---
    def test_model(self, user_id: str, model_id: str) -> dict:
        router = self.router_for(user_id)
        if router.registry.spec(model_id) is None:
            raise LLMServiceError(f"Modèle indisponible: {model_id}")
        req = CompletionRequest(
            messages=[Message(role="user", content="Réponds juste: OK")],
            model=model_id, max_tokens=8, temperature=0,
        )
        resp = router.registry.provider_for(model_id).complete(req)
        return {
            "ok": True, "model": resp.model, "provider": resp.provider,
            "latency_ms": round(resp.latency_ms, 1),
            "tokens": resp.usage.total_tokens,
            "cost_usd": round(resp.cost_usd, 6),
            "sample": resp.content[:120],
        }

    # --- Chat : complétion routée ---
    def complete(self, user_id: str, messages: list[dict], *,
                 strategy: str = "balanced", pinned_model: str | None = None,
                 require_privacy: str | None = None, needs_tools: bool = False,
                 temperature: float = 0.7, max_tokens: int | None = None) -> dict:
        router = self.router_for(user_id)
        if not router.registry.specs():
            raise LLMServiceError(
                "Aucun modèle disponible. Configurez un fournisseur cloud "
                "(OpenAI, Claude…) ou démarrez Ollama avec un modèle installé "
                "(ex: `ollama pull llama3.2`).")
        ctx = RoutingContext(
            needs_tools=needs_tools,
            pinned_model=pinned_model,
            require_privacy=Privacy(require_privacy) if require_privacy else None,
        )
        req = CompletionRequest(
            messages=[Message(role=m["role"], content=m["content"])
                      for m in _with_system(messages)],
            temperature=temperature, max_tokens=max_tokens or CHAT_MAX_TOKENS,
        )
        chosen = router.choose(ctx, strategy)
        resp = router.complete(req, ctx=ctx, strategy=strategy)
        return {
            "content": resp.content,
            "routing": {"strategy": strategy, "chosen_model": chosen.id,
                        "provider": resp.provider},
            "usage": {"prompt_tokens": resp.usage.prompt_tokens,
                      "completion_tokens": resp.usage.completion_tokens,
                      "cost_usd": round(resp.cost_usd, 6),
                      "latency_ms": round(resp.latency_ms, 1)},
        }

    def _prepare_messages(self, user_id: str, messages: list[dict],
                          use_memory: bool) -> list[dict]:
        """Ajoute le prompt système et, si demandé, la mémoire pertinente."""
        msgs = _with_system(messages)
        if use_memory:
            try:
                from .memory_service import MemoryService
                last = next((m["content"] for m in reversed(messages)
                             if m.get("role") == "user"), "")
                mem = MemoryService().recall_context(user_id, last)
                if mem:
                    msgs = [msgs[0], {"role": "system", "content": mem}, *msgs[1:]]
            except Exception:            # la mémoire ne doit jamais casser le chat
                pass
        return msgs

    # --- Chat en streaming (tokens au fil de l'eau) ---
    def stream(self, user_id: str, messages: list[dict], *,
               strategy: str = "balanced", pinned_model: str | None = None,
               require_privacy: str | None = None, use_memory: bool = True):
        """Génère les tokens progressivement. Renvoie d'abord le modèle choisi."""
        router = self.router_for(user_id, record_usage=False)
        if not router.registry.specs():
            raise LLMServiceError(
                "Aucun modèle disponible. Configurez un fournisseur ou démarrez Ollama.")
        ctx = RoutingContext(
            pinned_model=pinned_model,
            require_privacy=Privacy(require_privacy) if require_privacy else None,
        )
        chosen = router.choose(ctx, strategy)
        req = CompletionRequest(
            messages=[Message(role=m["role"], content=m["content"])
                      for m in self._prepare_messages(user_id, messages, use_memory)],
            max_tokens=CHAT_MAX_TOKENS)
        return chosen, router.stream(req, ctx=ctx, strategy=strategy)

    # --- Dashboards de consommation ---
    def consumption(self, user_id: str) -> dict:
        return {
            "summary": self.usage.summary_for_user(user_id),
            "by_model": self.usage.by_model_for_user(user_id),
        }

    def preview_routing(self, user_id: str, strategy: str = "balanced",
                        require_privacy: str | None = None) -> list[dict]:
        """Explique le routage : classement des modèles pour une stratégie donnée."""
        router = self.router_for(user_id)
        ctx = RoutingContext(
            require_privacy=Privacy(require_privacy) if require_privacy else None)
        return [{"rank": i + 1, "model": s.id, "provider": s.provider,
                 "quality": s.quality, "input_cost": s.input_cost, "speed": s.speed}
                for i, s in enumerate(router.rank(ctx, strategy))]
