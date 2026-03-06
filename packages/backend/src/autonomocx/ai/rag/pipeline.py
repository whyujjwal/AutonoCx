"""RAG pipeline -- orchestrates retrieval, embedding, chunking, and reranking."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.config import get_settings

from .chunker import TextChunk, TextChunker
from .embeddings import EmbeddingService
from .reranker import RankedResult, Reranker
from .retriever import ChunkResult, VectorRetriever

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A single retrieval result surfaced to the caller."""

    content: str
    source: str
    score: float
    chunk_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentChunkOutput:
    """Result of ingesting and chunking a document."""

    chunk_id: str
    content: str
    index: int
    embedding: list[float]
    token_count: int
    metadata: dict = field(default_factory=dict)


# ------------------------------------------------------------------
# Pipeline
# ------------------------------------------------------------------


class RAGPipeline:
    """End-to-end retrieval-augmented generation pipeline.

    Provides two main operations:
    - ``retrieve``: query -> embed -> vector search -> rerank -> results
    - ``ingest_document``: text -> chunk -> embed -> chunk objects
    """

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        retriever: VectorRetriever | None = None,
        reranker: Reranker | None = None,
        chunker: TextChunker | None = None,
    ) -> None:
        self._embedder = embedding_service or EmbeddingService()
        self._retriever = retriever or VectorRetriever()
        self._reranker = reranker or Reranker()
        self._chunker = chunker or TextChunker()

        settings = get_settings()
        self._reranker_enabled = settings.rag_reranker_enabled
        self._default_top_k = settings.rag_top_k
        self._chunk_size = settings.rag_chunk_size
        self._chunk_overlap = settings.rag_chunk_overlap

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        org_id: uuid.UUID,
        kb_ids: list[uuid.UUID],
        *,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """Execute the full retrieval pipeline for a user query.

        Steps:
        1. Embed the query.
        2. Vector search against specified knowledge bases.
        3. Optionally rerank results.
        4. Return top-k results.
        """
        top_k = top_k or self._default_top_k

        if not kb_ids:
            logger.debug("rag_retrieve_no_kbs", org_id=str(org_id))
            return []

        # 1. Embed query
        query_embedding = await self._embedder.embed_text(query)

        # 2. Vector search (fetch more than top_k if reranking)
        fetch_k = top_k * 3 if self._reranker_enabled else top_k
        chunks: list[ChunkResult] = await self._retriever.search(
            db,
            query_embedding=query_embedding,
            kb_ids=kb_ids,
            top_k=fetch_k,
        )

        if not chunks:
            logger.debug("rag_retrieve_no_results", query=query[:100], org_id=str(org_id))
            return []

        # 3. Rerank
        if self._reranker_enabled and len(chunks) > 1:
            ranked: list[RankedResult] = self._reranker.rerank(query, chunks, top_k=top_k)
            final_chunks = [(r.chunk, r.combined_score) for r in ranked]
        else:
            final_chunks = [(c, c.score) for c in chunks[:top_k]]

        # 4. Build results
        results: list[RetrievalResult] = []
        for chunk, score in final_chunks:
            source = chunk.metadata.get("source", "") or chunk.metadata.get("title", "")
            results.append(
                RetrievalResult(
                    content=chunk.content,
                    source=source,
                    score=score,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    metadata=chunk.metadata,
                )
            )

        logger.info(
            "rag_retrieve_done",
            query=query[:80],
            kb_count=len(kb_ids),
            results=len(results),
            top_score=results[0].score if results else 0.0,
        )
        return results

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    async def ingest_document(
        self,
        text: str,
        *,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        metadata: dict | None = None,
    ) -> list[DocumentChunkOutput]:
        """Chunk a document and generate embeddings for each chunk.

        Returns chunk objects ready to be persisted to the ``document_chunks``
        table (the caller is responsible for the actual DB insert).
        """
        chunk_size = chunk_size or self._chunk_size
        chunk_overlap = chunk_overlap or self._chunk_overlap

        # 1. Chunk
        text_chunks: list[TextChunk] = self._chunker.chunk_text(
            text,
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            metadata=metadata,
        )

        if not text_chunks:
            return []

        # 2. Embed all chunks in a batch
        texts = [c.content for c in text_chunks]
        embeddings = await self._embedder.embed_batch(texts)

        # 3. Build output
        outputs: list[DocumentChunkOutput] = []
        for chunk, embedding in zip(text_chunks, embeddings):
            # Rough token estimate: chars / 4
            token_count = len(chunk.content) // 4
            outputs.append(
                DocumentChunkOutput(
                    chunk_id=chunk.id,
                    content=chunk.content,
                    index=chunk.index,
                    embedding=embedding,
                    token_count=token_count,
                    metadata=chunk.metadata,
                )
            )

        logger.info(
            "rag_ingest_done",
            chunks=len(outputs),
            total_chars=sum(len(c.content) for c in text_chunks),
        )
        return outputs
