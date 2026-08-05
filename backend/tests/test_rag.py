"""Tests du moteur RAG — embedder déterministe (hashing), LLM factice, 0 réseau.

Couvre : découpage + overlap, déterminisme et sémantique des embeddings, BM25,
recherche hybride, et réponse citée du moteur.
Lancer :  python tests/test_rag.py   (depuis backend/)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.base import AgentLLMResponse
from app.rag import BM25, HashingEmbedder, RAGEngine, RecursiveChunker, cosine, hybrid_search


class FakeLLM:
    def __init__(self):
        self.last_messages = None

    def complete(self, messages, *, strategy="balanced", require_privacy=None,
                 pinned_model=None, agent=None):
        self.last_messages = messages
        return AgentLLMResponse(content="Réponse fondée sur le contexte [1].",
                                model="fake", provider="fake")


CORPUS = [
    "Les transformers utilisent le mécanisme d'attention pour traiter le langage naturel.",
    "La photosynthèse convertit la lumière en énergie chimique chez les plantes vertes.",
    "BM25 est une fonction de classement lexical très utilisée en recherche d'information.",
]


def _records(embedder):
    embs = embedder.embed_many(CORPUS)
    return [{"id": f"c{i}", "text": t, "embedding": e, "document_id": "d1",
             "title": "Doc", "ordinal": i} for i, (t, e) in enumerate(zip(CORPUS, embs))]


def test_chunking_overlap_and_ordinals():
    text = " ".join(f"Phrase numéro {i} sur le sujet étudié." for i in range(60))
    chunks = RecursiveChunker(chunk_tokens=30, overlap_tokens=8).split(text)
    assert len(chunks) >= 3
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))
    # Overlap : la fin d'un chunk se retrouve au début du suivant.
    prev_tail = chunks[0].text.split()[-3:]
    assert any(w in chunks[1].text.split()[:12] for w in prev_tail)
    print(f"[chunk]    {len(chunks)} chunks, ordinaux OK, overlap présent")


def test_embeddings_deterministic_and_semantic():
    emb = HashingEmbedder()
    assert emb.embed("réseaux de neurones") == emb.embed("réseaux de neurones")
    same = cosine(emb.embed("chat chien animal"), emb.embed("chat chien animal"))
    diff = cosine(emb.embed("chat chien animal"), emb.embed("moteur voiture route"))
    assert same > 0.99 and same > diff
    print(f"[embed]    déterministe; cosine(identique)={same:.2f} > cosine(différent)={diff:.2f}")


def test_bm25_ranks_rare_term():
    scores = BM25(CORPUS).scores("attention transformers")
    assert scores[0] == max(scores) and scores[0] > 0
    print(f"[bm25]     'attention transformers' -> doc 0 en tête ({scores[0]:.2f})")


def test_hybrid_search_finds_relevant():
    emb = HashingEmbedder()
    recs = _records(emb)
    hits = hybrid_search("Comment marche l'attention des transformers ?",
                         emb.embed("Comment marche l'attention des transformers ?"),
                         recs, k=2)
    assert hits[0].record["id"] == "c0"          # le passage pertinent
    assert hits[0].dense_rank and hits[0].sparse_rank
    print(f"[hybrid]   top: {hits[0].record['id']} (dense#{hits[0].dense_rank}, sparse#{hits[0].sparse_rank})")


def test_engine_answer_with_citations():
    emb = HashingEmbedder()
    llm = FakeLLM()
    engine = RAGEngine(emb, llm, top_k=2)
    res = engine.answer("Qu'est-ce que l'attention des transformers ?", _records(emb))
    assert res["used_chunks"] == 2
    assert [r["marker"] for r in res["references"]] == [1, 2]
    assert res["references"][0]["chunk_id"] == "c0"      # source la plus pertinente
    # Le prompt envoyé au LLM contient bien le contexte numéroté.
    assert "[1]" in llm.last_messages[-1].content
    print(f"[engine]   réponse citée; {res['used_chunks']} sources -> {[r['chunk_id'] for r in res['references']]}")


def test_engine_no_documents():
    res = RAGEngine(HashingEmbedder(), FakeLLM()).answer("question", [])
    assert res["used_chunks"] == 0 and res["references"] == []
    print("[engine]   aucun document -> réponse vide propre (pas d'appel LLM)")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests RAG passés.")
