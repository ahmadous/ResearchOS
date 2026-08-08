"""Factory Pattern pour les providers IA.

Un seul point de création. Ajouter un fournisseur = 1 ligne dans `_REGISTRY`.
La factory ne connaît que des *clés string* -> *classes* : c'est ce qui permet
d'ajouter dynamiquement un provider depuis la base de données (LLM Manager)
sans redéployer.
"""
from __future__ import annotations

from .base import LLMProvider, ProviderError
from .providers import (
    AnthropicProvider,
    DeepSeekProvider,
    GroqProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    OpenRouterProvider,
)

# clé logique -> classe de provider
_REGISTRY: dict[str, type[LLMProvider]] = {
    "openai": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    "openrouter": OpenRouterProvider,
    "deepseek": DeepSeekProvider,
    "groq": GroqProvider,
    # Providers compatibles-OpenAI : réutilisent la même classe, base_url différent.
    "qwen": OpenAICompatibleProvider,
    "mistral": OpenAICompatibleProvider,
    "grok": OpenAICompatibleProvider,
    "huggingface": OpenAICompatibleProvider,
    # "gemini": GeminiProvider,  # TODO Phase 2
}


class ProviderFactory:
    @staticmethod
    def available() -> list[str]:
        return sorted(_REGISTRY)

    @staticmethod
    def register(key: str, cls: type[LLMProvider]) -> None:
        """Permet aux plugins / marketplace d'enregistrer un provider à chaud."""
        _REGISTRY[key] = cls

    @staticmethod
    def create(
        key: str,
        api_key: str | None = None,
        base_url: str | None = None,
        **opts,
    ) -> LLMProvider:
        cls = _REGISTRY.get(key)
        if cls is None:
            raise ProviderError(
                key, f"fournisseur inconnu (disponibles: {ProviderFactory.available()})"
            )
        return cls(api_key=api_key, base_url=base_url, **opts)
