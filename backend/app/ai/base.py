"""
Abstractions de la couche IA.

Toute la plateforme dépend de ces interfaces, jamais d'un SDK concret.
C'est le point d'application du *Dependency Inversion Principle* (le "D" de SOLID) :
les couches hautes (agents, services) dépendent de `LLMProvider`, pas d'OpenAI/Claude/etc.

Ajouter un nouveau fournisseur = écrire une classe qui implémente `LLMProvider`,
puis l'enregistrer dans la factory. Aucun autre fichier ne change (Open/Closed).
"""
from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterator


class Modality(str, enum.Enum):
    TEXT = "text"
    VISION = "vision"
    EMBEDDING = "embedding"
    AUDIO = "audio"


class Privacy(str, enum.Enum):
    """Niveau de confidentialité d'un modèle — critère de routing."""
    LOCAL = "local"        # tourne sur la machine (Ollama, llama.cpp) : données jamais exposées
    CLOUD = "cloud"        # API tierce
    PRIVATE_CLOUD = "private_cloud"  # cloud dédié/on-prem


@dataclass(frozen=True)
class ModelSpec:
    """
    Carte d'identité d'un modèle. Alimente le routeur intelligent.
    Les coûts sont en USD par 1M de tokens. `speed` et `quality` sont des
    scores normalisés 0..1 (calibrés à la main / mis à jour via télémétrie).
    """
    id: str                      # ex: "gpt-4o", "claude-opus-4-8"
    provider: str                # ex: "openai", "anthropic"
    display_name: str
    modalities: tuple[Modality, ...] = (Modality.TEXT,)
    context_window: int = 8_192
    max_output: int = 4_096
    input_cost: float = 0.0      # USD / 1M tokens in
    output_cost: float = 0.0     # USD / 1M tokens out
    speed: float = 0.5           # 0 (lent) .. 1 (rapide)
    quality: float = 0.5         # 0 .. 1
    privacy: Privacy = Privacy.CLOUD
    supports_tools: bool = False
    supports_streaming: bool = True

    def supports(self, modality: Modality) -> bool:
        return modality in self.modalities


@dataclass
class Message:
    role: str                    # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None


@dataclass
class CompletionRequest:
    messages: list[Message]
    model: str | None = None     # None => laissé au routeur
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    tools: list[dict] | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class CompletionResponse:
    content: str
    model: str
    provider: str
    usage: Usage = field(default_factory=Usage)
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    raw: dict | None = None
    finish_reason: str | None = None


class ProviderError(Exception):
    """Erreur normalisée d'un provider (auth, quota, réseau, modèle inconnu)."""

    def __init__(self, provider: str, message: str, *, retryable: bool = False):
        self.provider = provider
        self.retryable = retryable
        super().__init__(f"[{provider}] {message}")


class LLMProvider(abc.ABC):
    """
    Interface commune à tous les fournisseurs (Strategy Pattern).

    Un provider encapsule UNE clé API + UN endpoint. Il expose le catalogue de
    modèles qu'il sait servir et sait exécuter une complétion (sync + stream).
    """

    name: str = "base"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **opts):
        self.api_key = api_key
        self.base_url = base_url
        self.opts = opts

    @abc.abstractmethod
    def models(self) -> list[ModelSpec]:
        """Catalogue statique des modèles servis par ce provider."""

    @abc.abstractmethod
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        """Complétion synchrone."""

    def stream(self, request: CompletionRequest) -> Iterator[str]:
        """Complétion en flux (tokens). Override si le provider le supporte."""
        raise NotImplementedError(f"{self.name} ne supporte pas le streaming")

    def health_check(self) -> bool:
        """Ping léger — utilisé par le LLM Manager pour tester une clé/modèle."""
        try:
            self.complete(CompletionRequest(
                messages=[Message(role="user", content="ping")],
                max_tokens=1,
            ))
            return True
        except Exception:
            return False

    # --- helpers partagés ---
    def _spec(self, model_id: str) -> ModelSpec | None:
        return next((m for m in self.models() if m.id == model_id), None)

    def estimate_cost(self, model_id: str, usage: Usage) -> float:
        spec = self._spec(model_id)
        if not spec:
            return 0.0
        return (usage.prompt_tokens * spec.input_cost
                + usage.completion_tokens * spec.output_cost) / 1_000_000
