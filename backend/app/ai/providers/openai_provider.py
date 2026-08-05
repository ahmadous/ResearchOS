"""Provider OpenAI (et compatible OpenAI : OpenRouter, DeepSeek, Qwen, Grok...).

Beaucoup de fournisseurs exposent l'API "chat/completions" d'OpenAI. On factorise
donc un provider générique compatible-OpenAI, paramétré par `base_url` + catalogue.
Les providers spécifiques (OpenRouter, DeepSeek...) en héritent juste en changeant
l'URL et la liste de modèles — DRY + Open/Closed.
"""
from __future__ import annotations

import time

from ..base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    Modality,
    ModelSpec,
    Privacy,
    ProviderError,
    Usage,
)


class OpenAICompatibleProvider(LLMProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **opts):
        super().__init__(api_key, base_url or self.default_base_url, **opts)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:  # pragma: no cover
                raise ProviderError(self.name, "SDK openai non installé") from e
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def models(self) -> list[ModelSpec]:
        return [
            ModelSpec("gpt-4o", "openai", "GPT-4o",
                      modalities=(Modality.TEXT, Modality.VISION),
                      context_window=128_000, max_output=16_384,
                      input_cost=2.5, output_cost=10.0,
                      speed=0.7, quality=0.9, privacy=Privacy.CLOUD,
                      supports_tools=True),
            ModelSpec("gpt-4o-mini", "openai", "GPT-4o mini",
                      modalities=(Modality.TEXT, Modality.VISION),
                      context_window=128_000, max_output=16_384,
                      input_cost=0.15, output_cost=0.6,
                      speed=0.9, quality=0.7, privacy=Privacy.CLOUD,
                      supports_tools=True),
        ]

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        client = self._get_client()
        model = request.model or self.models()[0].id
        started = time.perf_counter()
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                tools=request.tools,
            )
        except Exception as e:  # normalise l'erreur SDK
            raise ProviderError(self.name, str(e), retryable=True) from e

        latency = (time.perf_counter() - started) * 1000
        choice = resp.choices[0]
        usage = Usage(
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )
        return CompletionResponse(
            content=choice.message.content or "",
            model=model,
            provider=self.name,
            usage=usage,
            latency_ms=latency,
            cost_usd=self.estimate_cost(model, usage),
            finish_reason=choice.finish_reason,
        )

    def stream(self, request: CompletionRequest):
        client = self._get_client()
        model = request.model or self.models()[0].id
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": m.role, "content": m.content} for m in request.messages],
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise ProviderError(self.name, str(e), retryable=True) from e


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"

    def models(self) -> list[ModelSpec]:
        return [
            ModelSpec("meta-llama/llama-3.3-70b-instruct", "openrouter", "Llama 3.3 70B",
                      context_window=131_072, input_cost=0.12, output_cost=0.3,
                      speed=0.6, quality=0.82, supports_tools=True),
            ModelSpec("mistralai/mistral-large", "openrouter", "Mistral Large",
                      context_window=128_000, input_cost=2.0, output_cost=6.0,
                      speed=0.6, quality=0.85, supports_tools=True),
        ]


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"

    def models(self) -> list[ModelSpec]:
        return [
            ModelSpec("deepseek-chat", "deepseek", "DeepSeek V3",
                      context_window=64_000, input_cost=0.27, output_cost=1.1,
                      speed=0.7, quality=0.84, supports_tools=True),
            ModelSpec("deepseek-reasoner", "deepseek", "DeepSeek R1 (reasoning)",
                      context_window=64_000, input_cost=0.55, output_cost=2.19,
                      speed=0.4, quality=0.9, supports_tools=False),
        ]
