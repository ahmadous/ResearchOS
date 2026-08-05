"""Test de fumée du AI Router — aucune clé API requise.

On valide UNIQUEMENT la logique de sélection (scoring/éligibilité), pas les
appels réseau. Lancer :  python -m tests.test_router   (depuis backend/)
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai import AIRouter, ModelRegistry, ProviderConfig
from app.ai.base import Modality, Privacy
from app.ai.providers.ollama_provider import OllamaProvider
from app.ai.strategies import RoutingContext

# Ollama est simulé (démon non requis) : modèles locaux "installés".
_FAKE_OLLAMA = [
    {"name": "llama3.1:8b", "details": {"parameter_size": "8.0B"}},
    {"name": "qwen2.5:14b", "details": {"parameter_size": "14.8B"}},
    {"name": "mistral:7b", "details": {"parameter_size": "7.2B"}},
]
patch.object(OllamaProvider, "_fetch_installed", return_value=_FAKE_OLLAMA).start()

# On configure les providers SANS clés (on ne fait que lire les catalogues).
CONFIGS = [
    ProviderConfig("anthropic", api_key="test"),
    ProviderConfig("openai", api_key="test"),
    ProviderConfig("deepseek", api_key="test"),
    ProviderConfig("ollama"),  # local, pas de clé
]


def build_router() -> AIRouter:
    return AIRouter(ModelRegistry(CONFIGS), default_model="gpt-4o-mini")


def test_cost_strategy_prefers_cheapest():
    router = build_router()
    best = router.choose(RoutingContext(), strategy="cost")
    # Les modèles Ollama sont à 0 USD -> doivent gagner sur le coût.
    assert best.input_cost == 0.0, best.id
    print(f"[cost]     -> {best.display_name}  ({best.input_cost} USD/1M)")


def test_quality_strategy_prefers_best():
    router = build_router()
    best = router.choose(RoutingContext(), strategy="quality")
    assert best.quality >= 0.95, best.id
    print(f"[quality]  -> {best.display_name}  (q={best.quality})")


def test_privacy_forces_local():
    router = build_router()
    ctx = RoutingContext(require_privacy=Privacy.LOCAL)
    best = router.choose(ctx, strategy="balanced")
    assert best.privacy == Privacy.LOCAL, best.id
    print(f"[privacy]  -> {best.display_name}  ({best.privacy.value})")


def test_context_window_constraint():
    router = build_router()
    # 150k tokens : élimine tout modèle à fenêtre trop courte (ex: Ollama 32k).
    ctx = RoutingContext(min_context=150_000)
    best = router.choose(ctx, strategy="cost")
    assert best.context_window >= 150_000, best.id
    print(f"[ctx>150k] -> {best.display_name}  (ctx={best.context_window})")


def test_vision_modality_filter():
    router = build_router()
    ctx = RoutingContext(required_modality=Modality.VISION)
    ranked = router.rank(ctx, strategy="quality")
    assert all(Modality.VISION in s.modalities for s in ranked)
    print(f"[vision]   -> {[s.display_name for s in ranked]}")


def test_manual_pin_overrides_strategy():
    router = build_router()
    ctx = RoutingContext(pinned_model="deepseek-reasoner")
    best = router.choose(ctx, strategy="cost")  # cost dirait Ollama, mais on épingle
    assert best.id == "deepseek-reasoner"
    print(f"[pinned]   -> {best.display_name} (switch manuel respecté)")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests de routing passés.")
