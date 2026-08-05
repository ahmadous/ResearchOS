"""Couche IA de ResearchOS : providers, factory, registry, router, stratégies."""
from .base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    Message,
    Modality,
    ModelSpec,
    Privacy,
    ProviderError,
    Usage,
)
from .factory import ProviderFactory
from .router import AIRouter, ModelRegistry, ProviderConfig
from .strategies import RoutingContext, get_strategy

__all__ = [
    "CompletionRequest", "CompletionResponse", "Message", "Usage",
    "LLMProvider", "ModelSpec", "Modality", "Privacy", "ProviderError",
    "ProviderFactory", "AIRouter", "ModelRegistry", "ProviderConfig",
    "RoutingContext", "get_strategy",
]
