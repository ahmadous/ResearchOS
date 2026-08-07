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


def test_rag_answer_receives_language_directive():
    from app.agents.base import AgentLLMResponse
    from app.rag import HashingEmbedder, RAGEngine

    class FakeLLM:
        def __init__(self): self.sys = None
        def complete(self, messages, **kw):
            self.sys = messages[0].content
            return AgentLLMResponse(content="ok", model="f", provider="f")

    emb, llm = HashingEmbedder(), FakeLLM()
    recs = [{"id": "c1", "text": "attention transformers",
             "embedding": emb.embed("attention transformers"),
             "document_id": "d", "ordinal": 0, "title": "D"}]
    RAGEngine(emb, llm).answer("q", recs, system_extra=" Réponds OBLIGATOIREMENT en anglais.")
    assert "OBLIGATOIREMENT en anglais" in llm.sys
    print("[rag]      consigne de langue transmise au moteur RAG")


def test_agent_prompt_includes_language_directive():
    from app.agents.base import AgentContext, BaseAgent

    class A(BaseAgent):
        name = "a"
        system_prompt = "Prompt de base."

    ctx = AgentContext(goal="x", data={"lang_directive": " Réponds en anglais."})
    msgs = A(llm=None).build_messages("faire la tâche", ctx)
    assert "Prompt de base." in msgs[0].content and "Réponds en anglais" in msgs[0].content
    print("[agent]    directive de langue injectée dans le prompt de l'agent")


if __name__ == "__main__":
    for t in [test_detects_common_languages, test_short_or_unknown_returns_none,
              test_with_system_injects_language_instruction,
              test_with_system_respects_existing_system,
              test_rag_answer_receives_language_directive,
              test_agent_prompt_includes_language_directive]:
        t()
    print("\n✅ 6 tests langue passés.")
