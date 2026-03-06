"""TF-IDF based reranking of retrieval results.

This is a lightweight, dependency-free reranker that uses term-frequency /
inverse-document-frequency scoring to re-order results by relevance to the
query.  It avoids external model calls and adds negligible latency.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

import structlog

from .retriever import ChunkResult

logger = structlog.get_logger(__name__)

# Common English stop-words to exclude from TF-IDF
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "it", "this", "that", "was", "are", "be",
    "has", "had", "have", "do", "does", "did", "will", "would", "can",
    "could", "should", "may", "might", "from", "not", "no", "so", "if",
    "as", "we", "i", "you", "he", "she", "they", "me", "my", "your",
    "our", "his", "her", "its", "them", "been", "being", "were", "am",
})


@dataclass(frozen=True, slots=True)
class RankedResult:
    """A chunk result augmented with a reranking score."""

    chunk: ChunkResult
    original_score: float
    rerank_score: float
    combined_score: float


class Reranker:
    """Re-score retrieval results using TF-IDF similarity to the query."""

    def __init__(
        self,
        *,
        vector_weight: float = 0.6,
        tfidf_weight: float = 0.4,
    ) -> None:
        if not math.isclose(vector_weight + tfidf_weight, 1.0, abs_tol=0.01):
            raise ValueError("Weights must sum to 1.0")
        self._vector_weight = vector_weight
        self._tfidf_weight = tfidf_weight

    def rerank(
        self,
        query: str,
        results: list[ChunkResult],
        top_k: int = 5,
    ) -> list[RankedResult]:
        """Re-rank *results* by combined vector + TF-IDF score."""
        if not results:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            # No usable query terms; fall back to original ranking
            return [
                RankedResult(
                    chunk=r,
                    original_score=r.score,
                    rerank_score=0.0,
                    combined_score=r.score,
                )
                for r in results[:top_k]
            ]

        # Build IDF from the result corpus
        doc_count = len(results)
        doc_freq: Counter[str] = Counter()
        doc_tokens: list[Counter[str]] = []
        for chunk in results:
            tokens = self._tokenize(chunk.content)
            tf = Counter(tokens)
            doc_tokens.append(tf)
            for term in set(tokens):
                doc_freq[term] += 1

        idf: dict[str, float] = {}
        for term, df in doc_freq.items():
            idf[term] = math.log((doc_count + 1) / (df + 1)) + 1.0

        # Compute TF-IDF vector for the query
        query_tf = Counter(query_tokens)
        query_vec: dict[str, float] = {}
        for term, count in query_tf.items():
            query_vec[term] = count * idf.get(term, 1.0)

        # Score each result
        ranked: list[RankedResult] = []
        for chunk, tf in zip(results, doc_tokens):
            doc_vec: dict[str, float] = {}
            for term, count in tf.items():
                doc_vec[term] = count * idf.get(term, 1.0)

            tfidf_sim = self._cosine_sim(query_vec, doc_vec)
            combined = (
                self._vector_weight * chunk.score
                + self._tfidf_weight * tfidf_sim
            )
            ranked.append(
                RankedResult(
                    chunk=chunk,
                    original_score=chunk.score,
                    rerank_score=tfidf_sim,
                    combined_score=combined,
                )
            )

        ranked.sort(key=lambda r: r.combined_score, reverse=True)

        logger.debug(
            "rerank_complete",
            input_count=len(results),
            output_count=min(top_k, len(ranked)),
        )

        return ranked[:top_k]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lowercase, split on non-alphanumeric, and remove stop words."""
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]

    @staticmethod
    def _cosine_sim(a: dict[str, float], b: dict[str, float]) -> float:
        """Cosine similarity between two sparse vectors represented as dicts."""
        if not a or not b:
            return 0.0
        dot = sum(a.get(k, 0.0) * b.get(k, 0.0) for k in set(a) | set(b))
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
