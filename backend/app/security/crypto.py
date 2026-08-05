"""Chiffrement symétrique des secrets (clés API des providers).

On ne stocke JAMAIS une clé API en clair. À l'écriture on chiffre (Fernet),
à la lecture on déchiffre juste-à-temps pour instancier le provider.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet
from flask import current_app


def _fernet() -> Fernet:
    key = current_app.config.get("CREDENTIAL_KEY")
    if not key:
        # Dev : dérive une clé déterministe du SECRET_KEY (NE PAS utiliser en prod).
        digest = hashlib.sha256(current_app.config["SECRET_KEY"].encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    elif isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    return _fernet().decrypt(ciphertext.encode()).decode()


def mask(secret: str) -> str:
    """Représentation sûre pour l'UI : sk-...ab12."""
    if not secret or len(secret) < 8:
        return "••••"
    return f"{secret[:3]}…{secret[-4:]}"
