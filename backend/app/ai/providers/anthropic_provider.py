"""Provider Anthropic (Claude).

L'API Claude a une forme différente d'OpenAI : le message `system` est un
paramètre à part, pas un rôle dans `messages`. Le provider absorbe cette
différence pour que les couches hautes gardent une interface uniforme.
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


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **opts):
        super().__init__(api_key, base_url, **opts)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError as e:  # pragma: no cover
                raise ProviderError(self.name, "SDK anthropic non installé") from e
            self._client = Anthropic(api_key=self.api_key, base_url=self.base_url)
        return self._client

    def models(self) -> list[ModelSpec]:
        return [
            ModelSpec("claude-opus-4-8", "anthropic", "Claude Opus 4.8",
                      modalities=(Modality.TEXT, Modality.VISION),
                      context_window=200_000, max_output=32_000,
                      input_cost=15.0, output_cost=75.0,
                      speed=0.5, quality=0.98, privacy=Privacy.CLOUD,
                      supports_tools=True),
            ModelSpec("claude-sonnet-5", "anthropic", "Claude Sonnet 5",
                      modalities=(Modality.TEXT, Modality.VISION),
                      context_window=200_000, max_output=16_000,
                      input_cost=3.0, output_cost=15.0,
                      speed=0.75, quality=0.92, privacy=Privacy.CLOUD,
                      supports_tools=True),
            ModelSpec("claude-haiku-4-5", "anthropic", "Claude Haiku 4.5",
                      context_window=200_000, max_output=8_000,
                      input_cost=1.0, output_cost=5.0,
                      speed=0.95, quality=0.8, privacy=Privacy.CLOUD,
                      supports_tools=True),
        ]

    @staticmethod
    def _split_system(request: CompletionRequest) -> tuple[str | None, list[dict]]:
        system = None
        msgs: list[dict] = []
        for m in request.messages:
            if m.role == "system":
                system = (system + "\n" + m.content) if system else m.content
            else:
                msgs.append({"role": m.role, "content": m.content})
        return system, msgs

    def complete(self, request: CompletionRequest) -> CompletionResponse:
        client = self._get_client()
        model = request.model or self.models()[1].id  # défaut : Sonnet
        system, msgs = self._split_system(request)
        started = time.perf_counter()
        try:
            resp = client.messages.create(
                model=model,
                system=system or "",
                messages=msgs,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 4096,
                tools=request.tools or [],
            )
        except Exception as e:
            raise ProviderError(self.name, str(e), retryable=True) from e

        latency = (time.perf_counter() - started) * 1000
        text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        usage = Usage(prompt_tokens=resp.usage.input_tokens,
                      completion_tokens=resp.usage.output_tokens)
        return CompletionResponse(
            content=text,
            model=model,
            provider=self.name,
            usage=usage,
            latency_ms=latency,
            cost_usd=self.estimate_cost(model, usage),
            finish_reason=resp.stop_reason,
        )

    def stream(self, request: CompletionRequest):
        client = self._get_client()
        model = request.model or self.models()[1].id
        system, msgs = self._split_system(request)
        try:
            with client.messages.stream(
                model=model, system=system or "", messages=msgs,
                temperature=request.temperature,
                max_tokens=request.max_tokens or 4096,
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise ProviderError(self.name, str(e), retryable=True) from e
