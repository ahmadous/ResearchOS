from .aggregator import ScholarAggregator
from .base import Paper, PaperSource
from .sources import (
    ArxivSource,
    CrossRefSource,
    HALSource,
    OpenAlexSource,
    SemanticScholarSource,
    SOURCES,
)

__all__ = [
    "Paper", "PaperSource", "ScholarAggregator", "SOURCES",
    "ArxivSource", "OpenAlexSource", "SemanticScholarSource",
    "CrossRefSource", "HALSource",
]
