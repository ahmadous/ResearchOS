"""BM25 — composante « sparse » (lexicale) de la recherche hybride.

Implémentation Okapi BM25 standard, en Python pur. Complète la recherche dense :
BM25 excelle sur les correspondances exactes de termes rares, là où les
embeddings capturent la proximité sémantique.
"""
from __future__ import annotations

import math
from collections import Counter

from .embeddings import tokenize


class BM25:
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [tokenize(d) for d in corpus]
        self.N = len(self.docs)
        self.doc_len = [len(d) for d in self.docs]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.tf = [Counter(d) for d in self.docs]
        # document frequency par terme
        df: Counter = Counter()
        for d in self.docs:
            for term in set(d):
                df[term] += 1
        # idf lissé (toujours positif)
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
                    for t, n in df.items()}

    def scores(self, query: str) -> list[float]:
        q_terms = tokenize(query)
        out = [0.0] * self.N
        for i in range(self.N):
            dl = self.doc_len[i] or 1
            denom_base = self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
            s = 0.0
            for term in q_terms:
                if term not in self.idf:
                    continue
                f = self.tf[i].get(term, 0)
                if f:
                    s += self.idf[term] * (f * (self.k1 + 1)) / (f + denom_base)
            out[i] = s
        return out
