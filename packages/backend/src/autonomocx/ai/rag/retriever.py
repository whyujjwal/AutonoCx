"""pgvector-based similarity search over document chunks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ChunkResult:
    """A single result from vector similarity search."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    knowledge_base_id: uuid.UUID
    content: str
    score: float  # cosine similarity (higher is better)
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


class VectorRetriever:
    """Perform cosine-similarity search against ``document_chunks`` using pgvector."""

    def __init__(self, similarity_threshold: float | None = None, top_k: int | None = None):
        settings = get_settings()
        self._threshold = similarity_threshold or settings.rag_similarity_threshold
        self._default_top_k = top_k or settings.rag_top_k

    async def search(
        self,
        db: AsyncSession,
        query_embedding: list[float],
        kb_ids: list[uuid.UUID],
        *,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[ChunkResult]:
        """Search for the most similar chunks across one or more knowledge bases.

        Uses the pgvector ``<=>`` (cosine distance) operator.  Cosine distance
        is ``1 - cosine_similarity``, so we convert to similarity for scoring.
        """
        top_k = top_k or self._default_top_k
        threshold = threshold or self._threshold

        if not kb_ids:
            return []

        # Build the embedding literal for pgvector
        embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # Raw SQL because SQLAlchemy does not natively expose <=> operator
        query = sa_text("""
            SELECT
                dc.id            AS chunk_id,
                dc.document_id   AS document_id,
                dc.knowledge_base_id AS knowledge_base_id,
                dc.content       AS content,
                dc.chunk_index   AS chunk_index,
                dc.metadata      AS metadata,
                1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM document_chunks dc
            JOIN knowledge_bases kb ON kb.id = dc.knowledge_base_id
            WHERE dc.knowledge_base_id = ANY(:kb_ids)
              AND kb.is_active = true
              AND dc.embedding IS NOT NULL
              AND 1 - (dc.embedding <=> CAST(:embedding AS vector)) >= :threshold
            ORDER BY similarity DESC
            LIMIT :top_k
        """)

        result = await db.execute(
            query,
            {
                "embedding": embedding_literal,
                "kb_ids": [str(kid) for kid in kb_ids],
                "threshold": threshold,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        chunks: list[ChunkResult] = []
        for row in rows:
            chunks.append(
                ChunkResult(
                    chunk_id=row.chunk_id,
                    document_id=row.document_id,
                    knowledge_base_id=row.knowledge_base_id,
                    content=row.content,
                    score=float(row.similarity),
                    chunk_index=row.chunk_index,
                    metadata=row.metadata or {},
                )
            )

        logger.debug(
            "vector_search",
            kb_count=len(kb_ids),
            results=len(chunks),
            top_score=chunks[0].score if chunks else 0.0,
        )
        return chunks
