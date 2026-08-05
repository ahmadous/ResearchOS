"""Embeddings — interface + implémentations (Strategy).

- `HashingEmbedder` : déterministe, sans réseau (bag-of-words hachés, L2-normalisé).
  Deux textes partageant du vocabulaire ont une similarité cosinus élevée →
  suffisant pour un RAG hors-ligne et pour des tests reproductibles.
- `OllamaEmbedder` : embeddings locaux de qualité via Ollama (nomic-embed-text…).

La factory choisit selon la config, avec repli automatique sur le hachage si le
backend demandé est indisponible (cohérent avec l'esprit Ollama-first).
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

_TOKEN = re.compile(r"[a-zà-ÿ0-9]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


class Embedder(Protocol):
    dim: int
    name: str

    def embed(self, text: str) -> list[float]: ...

    def embed_many(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Feature hashing déterministe : token -> bucket via SHA1, signe stable."""
    name = "hashing"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            h = int(hashlib.sha1(tok.encode()).hexdigest(), 16)
            bucket = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[bucket] += sign
        return l2_normalize(vec)

    def embed_many(self, texts):
        return [self.embed(t) for t in texts]


class OllamaEmbedder:
    """Embeddings via l'API Ollama (/api/embeddings). Local, gratuit."""
    name = "ollama"

    def __init__(self, model: str = "nomic-embed-text",
                 base_url: str = "http://localhost:11434", dim: int = 768):
        self.model = model
        self.base_url = base_url
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        r = httpx.post(f"{self.base_url}/api/embeddings",
                       json={"model": self.model, "prompt": text}, timeout=60)
        r.raise_for_status()
        emb = r.json().get("embedding") or []
        self.dim = len(emb) or self.dim
        return emb

    def embed_many(self, texts):
        return [self.embed(t) for t in texts]

    def is_up(self) -> bool:
        try:
            self.embed("ping")
            return True
        except httpx.HTTPError:
            return False


def get_embedder(backend: str = "hashing", *, model: str = "nomic-embed-text",
                 base_url: str = "http://localhost:11434") -> Embedder:
    """Fabrique l'embedder demandé, avec repli sur le hachage si indisponible."""
    if backend == "ollama":
        emb = OllamaEmbedder(model=model, base_url=base_url)
        if emb.is_up():
            return emb
        # Ollama/embeddings indisponible -> repli déterministe, pas de crash.
    return HashingEmbedder()
