"""Tests de la détection automatique de langue du chat.

Lancer : python tests/test_language.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.llm_service import _detect_language, _with_system


def test_detects_common_languages():
    assert _detect_language("Hello, what is a transformer in AI?") == "anglais"
    assert _detect_language("Bonjour, explique la photosynthèse en détail") == "français"
    assert _detect_language("Hola, ¿qué es la fotosíntesis exactamente?") == "espagnol"
    assert _detect_language("Ciao, che cosa è un transformer nella IA?") == "italien"
    print("[detect]   en/fr/es/it correctement détectés")


def test_short_or_unknown_returns_none():
    assert _detect_language("ok") is None                 # trop court
    assert _detect_language("Naka nga def ci sa liggéey") is None  # wolof -> inconnu
    print("[detect]   texte court / wolof -> None (repli sur mirror)")


def test_with_system_injects_language_instruction():
    msgs = _with_system([{"role": "user", "content": "Hello, what is a transformer in AI?"}])
    assert msgs[0]["role"] == "system"
    assert "anglais" in msgs[0]["content"] and "OBLIGATOIREMENT" in msgs[0]["content"]
    print("[inject]   consigne 'réponds en anglais' injectée")


def test_with_system_respects_existing_system():
    msgs = _with_system([{"role": "system", "content": "custom"},
                         {"role": "user", "content": "Hello there friend"}])
    assert msgs == [{"role": "system", "content": "custom"},
                    {"role": "user", "content": "Hello there friend"}]
    print("[inject]   système existant respecté (pas de double)")


if __name__ == "__main__":
    for t in [test_detects_common_languages, test_short_or_unknown_returns_none,
              test_with_system_injects_language_instruction,
              test_with_system_respects_existing_system]:
        t()
    print("\n✅ 4 tests langue passés.")
