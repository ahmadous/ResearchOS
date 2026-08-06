"""Provider Ollama — modèles LOCAUX, découverts dynamiquement.

Principe (demande utilisateur) : on ne code AUCUNE liste de modèles en dur.
On interroge le démon Ollama (`GET /api/tags`) pour connaître les modèles
RÉELLEMENT installés sur la machine, et c'est parmi eux que l'utilisateur choisit.

Robustesse : si Ollama est éteint/injoignable, `models()` renvoie une liste vide
(aucune exception) — le socle reste silencieux plutôt que de casser la plateforme.

Coût = 0, confidentialité = LOCAL : le routeur privilégie ces modèles dès que la
confidentialité prime ou qu'aucun fournisseur cloud n'est configuré.
"""
from __future__ import annotations

import os
import re
import time

import httpx

# Garde le modèle chargé en mémoire entre deux requêtes -> évite le rechargement
# (plusieurs secondes) à chaque message. Configurable via l'env.
_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")


def _options(request) -> dict:
    opts = {"temperature": request.temperature}
    if request.max_tokens:                       # borne la longueur -> plus rapide
        opts["num_predict"] = request.max_tokens
    return opts

from ..base import (
    CompletionRequest,
    CompletionResponse,
    LLMProvider,
    ModelSpec,
    Privacy,
    ProviderError,
    Usage,
)

# Cache court des specs découvertes : évite de pinger Ollama à chaque appel du
# routeur (qui liste les modèles très souvent).
_CACHE_TTL = 15.0  # secondes


def _parse_params_billions(name: str, details: dict) -> float | None:
    """Extrait la taille du modèle en milliards de paramètres (ex: 8.0 pour 8B)."""
    raw = (details or {}).get("parameter_size")  # ex: "8.0B", "7B", "70B"
    if not raw:
        m = re.search(r"(\d+(?:\.\d+)?)\s*b", name, re.IGNORECASE)  # ex: "llama3.1:8b"
        raw = m.group(0) if m else None
    if not raw:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", str(raw))
    return float(m.group(1)) if m else None


def _heuristics(params_b: float | None) -> tuple[float, float]:
    """(quality, speed) estimés d'après la taille. Plus gros = meilleur mais + lent."""
    if params_b is None:
        return 0.7, 0.75
    table = [
        (2, 0.55, 0.95),
        (4, 0.63, 0.90),
        (9, 0.72, 0.85),
        (15, 0.80, 0.62),
        (35, 0.86, 0.45),
        (float("inf"), 0.91, 0.30),
    ]
    for ceiling, quality, speed in table:
        if params_b < ceiling:
            return quality, speed
    return 0.91, 0.30


class OllamaProvider(LLMProvider):
    name = "ollama"
    default_base_url = "http://localhost:11434"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **opts):
        super().__init__(api_key, base_url or self.default_base_url, **opts)
        self._specs_cache: list[ModelSpec] = []
        self._cache_at: float = 0.0

    # --- Découverte dynamique ---
    def _fetch_installed(self) -> list[dict]:
        """Liste brute des modèles installés via l'API Ollama. [] si injoignable."""
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            r.raise_for_status()
            return r.json().get("models", [])
        except (httpx.HTTPError, ValueError):
            return []

    def models(self) -> list[ModelSpec]:
        now = time.monotonic()
        if self._specs_cache and (now - self._cache_at) < _CACHE_TTL:
            return self._specs_cache

        specs: list[ModelSpec] = []
        for m in self._fetch_installed():
            model_id = m.get("name") or m.get("model")
            if not model_id:
                continue
            details = m.get("details", {}) or {}
            params_b = _parse_params_billions(model_id, details)
            quality, speed = _heuristics(params_b)
            # /api/tags expose parfois le contexte réel et les capacités : on les
            # utilise si présents, sinon défaut prudent.
            ctx = details.get("context_length") or self.opts.get("context_window", 8192)
            caps = m.get("capabilities") or []
            specs.append(ModelSpec(
                id=model_id,
                provider=self.name,
                display_name=f"{model_id} (local)",
                context_window=int(ctx),
                max_output=2048,
                input_cost=0.0, output_cost=0.0,
                speed=speed, quality=quality,
                privacy=Privacy.LOCAL,
                supports_tools="tools" in caps,
            ))
        self._specs_cache = specs
        self._cache_at = now
        return specs

    def is_up(self) -> bool:
        """Le démon Ollama répond-il ? (utilisé par le LLM Manager)."""
        try:
            httpx.get(f"{self.base_url}/api/tags", timeout=3).raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    # --- Complétion ---
    def complete(self, request: CompletionRequest) -> CompletionResponse:
        model = request.model or (self.models()[0].id if self.models() else None)
        if not model:
            raise ProviderError(self.name,
                                "aucun modèle Ollama installé (essayez: ollama pull llama3.2)")
        started = time.perf_counter()
        try:
            r = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content}
                                 for m in request.messages],
                    "stream": False,
                    "keep_alive": _KEEP_ALIVE,
                    "options": _options(request),
                },
                timeout=180,
            )
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPError as e:
            raise ProviderError(self.name, str(e), retryable=True) from e

        latency = (time.perf_counter() - started) * 1000
        usage = Usage(prompt_tokens=data.get("prompt_eval_count", 0),
                      completion_tokens=data.get("eval_count", 0))
        return CompletionResponse(
            content=data.get("message", {}).get("content", ""),
            model=model, provider=self.name, usage=usage,
            latency_ms=latency, cost_usd=0.0,
            finish_reason=data.get("done_reason"),
        )

    def stream(self, request: CompletionRequest):
        import json
        model = request.model or (self.models()[0].id if self.models() else None)
        if not model:
            raise ProviderError(self.name, "aucun modèle Ollama installé")
        try:
            with httpx.stream(
                "POST", f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": m.role, "content": m.content}
                                 for m in request.messages],
                    "stream": True,
                    "keep_alive": _KEEP_ALIVE,
                    "options": _options(request),
                },
                timeout=180,
            ) as r:
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = chunk.get("message", {}).get("content", "")
                    if piece:
                        yield piece
        except httpx.HTTPError as e:
            raise ProviderError(self.name, str(e), retryable=True) from e
