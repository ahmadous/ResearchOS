"""Hachage de mots de passe — PBKDF2-HMAC-SHA256 (stdlib, zéro dépendance).

Format stocké :  pbkdf2$<iterations>$<salt_hex>$<hash_hex>
Comparaison en temps constant (hmac.compare_digest) contre les attaques timing.

Note : bcrypt/argon2 restent préférables en prod ; l'interface `hash_password`
/`verify_password` est identique, donc on peut basculer sans toucher aux services.
"""
from __future__ import annotations

import hashlib
import hmac
import os

_ALGO = "sha256"
_ITER = 240_000
_SALT_BYTES = 16


def hash_password(raw: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_ALGO, raw.encode("utf-8"), salt, _ITER)
    return f"pbkdf2${_ITER}${salt.hex()}${dk.hex()}"


def verify_password(raw: str, stored: str) -> bool:
    try:
        scheme, iters, salt_hex, hash_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        dk = hashlib.pbkdf2_hmac(_ALGO, raw.encode("utf-8"),
                                 bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False
