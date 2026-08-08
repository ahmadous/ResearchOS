"""Détection de langue partagée (chat, RAG, agents).

Détection déterministe via langdetect -> consigne explicite « réponds en {langue} »,
bien plus fiable qu'espérer que le modèle détecte lui-même. Repli « mirror » quand
la langue est inconnue (ex: wolof) ou trop courte.
"""
from __future__ import annotations

_LANG_NAMES = {"en": "anglais", "fr": "français", "es": "espagnol", "it": "italien",
               "pt": "portugais", "de": "allemand", "ar": "arabe", "nl": "néerlandais"}

MIRROR = " Réponds dans la MÊME langue que l'utilisateur (y compris wolof ou un mélange)."


def detect_language(text: str) -> str | None:
    text = (text or "").strip()
    if len(text) < 8:            # trop court pour une détection fiable
        return None
    try:
        from langdetect import DetectorFactory, detect_langs
        DetectorFactory.seed = 0
        top = detect_langs(text)[0]
        if top.prob >= 0.80 and top.lang in _LANG_NAMES:
            return _LANG_NAMES[top.lang]
    except Exception:
        pass
    return None


# Codes (sélecteur UI) -> nom de langue pour la consigne.
_CODE_NAMES = {"fr": "français", "en": "anglais", "es": "espagnol", "it": "italien",
               "pt": "portugais", "de": "allemand", "ar": "arabe",
               "nl": "néerlandais", "wo": "wolof"}


def language_directive(text: str) -> str:
    """Consigne pour la langue, en AUTO-détection sur le texte."""
    lang = detect_language(text)
    if lang:
        return f" IMPORTANT : le message est en {lang}. Réponds OBLIGATOIREMENT en {lang}."
    return MIRROR


# Consigne ÉCRITE DANS LA LANGUE CIBLE : bien mieux suivie par les petits modèles.
_FORCE = {
    "en": " Respond ONLY in English, whatever the language of the message.",
    "fr": " Réponds UNIQUEMENT en français, quelle que soit la langue du message.",
    "es": " Responde ÚNICAMENTE en español, sin importar el idioma del mensaje.",
    "it": " Rispondi SOLO in italiano, qualunque sia la lingua del messaggio.",
    "de": " Antworte NUR auf Deutsch, unabhängig von der Sprache der Nachricht.",
    "pt": " Responde APENAS em português, seja qual for a língua da mensagem.",
    "nl": " Antwoord ALLEEN in het Nederlands, ongeacht de taal van het bericht.",
    "ar": " أجب فقط باللغة العربية مهما كانت لغة الرسالة.",
    "wo": " Tontu ci wolof rekk (réponds uniquement en wolof).",
}


def directive_for(lang: str | None, text: str) -> str:
    """Consigne selon le CHOIX de l'utilisateur : langue imposée, ou 'auto'."""
    if lang and lang not in ("auto", ""):
        return _FORCE.get(lang, f" Réponds OBLIGATOIREMENT en {_CODE_NAMES.get(lang, lang)}.")
    return language_directive(text)
