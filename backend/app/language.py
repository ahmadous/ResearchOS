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


def language_directive(text: str) -> str:
    """Consigne à ajouter au prompt système pour forcer la langue de réponse."""
    lang = detect_language(text)
    if lang:
        return f" IMPORTANT : le message est en {lang}. Réponds OBLIGATOIREMENT en {lang}."
    return MIRROR
