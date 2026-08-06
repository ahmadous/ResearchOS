"""Tests de la recherche scientifique — parsing PUR + agrégation, 0 réseau.

Chaque source est testée sur un payload réel. L'agrégateur est testé avec des
sources factices (dédup, classement, robustesse aux pannes).
Lancer :  python tests/test_scholar.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scholar import (
    ArxivSource, CrossRefSource, HALSource, OpenAlexSource,
    Paper, PaperSource, ScholarAggregator, SemanticScholarSource,
)

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <published>2017-06-12T00:00:00Z</published>
    <title>Attention Is All You Need</title>
    <summary>The dominant sequence transduction models are based on attention.</summary>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <arxiv:doi>10.5555/attn</arxiv:doi>
  </entry>
</feed>"""

OPENALEX = {"results": [{
    "id": "https://openalex.org/W1", "title": "Attention Is All You Need",
    "publication_year": 2017, "cited_by_count": 90000,
    "doi": "https://doi.org/10.5555/attn",
    "authorships": [{"author": {"display_name": "Ashish Vaswani"}}],
    "host_venue": {"display_name": "NeurIPS"},
    "abstract_inverted_index": {"The": [0], "transformer": [1], "model": [2]}}]}

SEMANTIC = {"data": [{
    "paperId": "abc", "title": "BERT", "abstract": "We introduce BERT.",
    "year": 2019, "citationCount": 50000, "venue": "NAACL", "url": "http://x",
    "authors": [{"name": "Jacob Devlin"}], "externalIds": {"DOI": "10.18653/N19"}}]}

CROSSREF = {"message": {"items": [{
    "DOI": "10.1/x", "title": ["A Great Paper"],
    "author": [{"given": "Jane", "family": "Doe"}],
    "issued": {"date-parts": [[2020]]}, "container-title": ["Nature"],
    "URL": "http://doi", "is-referenced-by-count": 12}]}}

HAL = {"response": {"docs": [{
    "title_s": ["Un article de recherche"], "authFullName_s": ["Paul Dupont"],
    "abstract_s": ["Le résumé en français."], "doiId_s": "10.2/y",
    "uri_s": "https://hal.science/abc", "producedDateY_i": 2021}]}}


def test_parse_arxiv():
    p = ArxivSource().parse(ARXIV_XML)[0]
    assert p.title == "Attention Is All You Need" and p.year == 2017
    assert p.authors == ["Ashish Vaswani", "Noam Shazeer"] and p.doi == "10.5555/attn"
    print(f"[arxiv]    {p.title} ({p.year}) — {len(p.authors)} auteurs")


def test_parse_openalex_reconstructs_abstract():
    p = OpenAlexSource().parse(OPENALEX)[0]
    assert p.abstract == "The transformer model"          # index inversé reconstruit
    assert p.doi == "10.5555/attn" and p.citations == 90000 and p.venue == "NeurIPS"
    print(f"[openalex] abstract reconstruit: '{p.abstract}', {p.citations} citations")


def test_parse_semantic_scholar():
    p = SemanticScholarSource().parse(SEMANTIC)[0]
    assert p.title == "BERT" and p.doi == "10.18653/N19" and p.citations == 50000
    print(f"[s2]       {p.title} — DOI {p.doi}")


def test_parse_crossref():
    p = CrossRefSource().parse(CROSSREF)[0]
    assert p.title == "A Great Paper" and p.authors == ["Jane Doe"] and p.year == 2020
    assert p.venue == "Nature"
    print(f"[crossref] {p.title} — {p.authors[0]}, {p.venue}")


def test_parse_hal():
    p = HALSource().parse(HAL)[0]
    assert p.title == "Un article de recherche" and p.doi == "10.2/y" and p.year == 2021
    print(f"[hal]      {p.title} ({p.year})")


def test_dedup_keeps_richest():
    poor = Paper(title="Attention", source="crossref", doi="10.5555/attn")
    rich = Paper(title="Attention Is All You Need", source="openalex",
                 doi="10.5555/attn", abstract="riche", year=2017, citations=90000)
    merged = ScholarAggregator._dedup([poor, rich])
    assert len(merged) == 1 and merged[0].abstract == "riche"
    print("[dedup]    même DOI -> garde la version la plus complète")


class _Fake(PaperSource):
    name = "fake"
    default_base_url = "x"

    def __init__(self, papers, fail=False):
        super().__init__()
        self._papers, self._fail = papers, fail

    def _fetch(self, query, limit):
        if self._fail:
            raise RuntimeError("réseau HS")
        return None

    def parse(self, raw):
        return self._papers


def test_aggregator_sorts_and_survives_failures():
    a = Paper(title="A", source="fake", doi="d1", citations=10, year=2019)
    b = Paper(title="B", source="fake", doi="d2", citations=500, year=2021)
    agg = ScholarAggregator([_Fake([a, b]), _Fake([], fail=True)])
    out = agg.search("q")
    assert [r["title"] for r in out["results"]] == ["B", "A"]   # tri par citations
    assert "fake" in out["errors"]                              # panne capturée
    print(f"[agg]      classé par citations, panne d'une source capturée")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"\n✅ {len(tests)} tests scholar passés.")
