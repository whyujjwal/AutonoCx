"""Batch embedding generation worker.

Processes document chunks that have been created by the document
processor but do not yet have embeddings.  Calls the configured
embedding model (e.g. OpenAI ``text-embedding-3-small``) in batches
to generate vector representations.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.config import get_settings
from autonomocx.models.knowledge import DocumentChunk

logger = structlog.get_logger(__name__)

# Maximum chunks per API call (OpenAI supports up to 2048)
DEFAULT_BATCH_SIZE = 100


class EmbeddingWorker:
    """Generates embeddings for document chunks in batches."""

    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE) -> None:
        self.batch_size = batch_size
        self._settings = get_settings()

    async def process_unembedded_chunks(self, db: AsyncSession) -> int:
        """Find chunks without embeddings and generate them in batches.

        Returns the total number of chunks that were embedded.

        Flow:
            1. Query for chunks where embedding IS NULL
            2. Batch chunks by ``batch_size``
            3. Call the embedding API for each batch
            4. Update chunk rows with the resulting vectors
        """
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.created_at)
            .limit(self.batch_size * 10)  # cap per run
        )
        chunks = list(result.scalars().all())

        if not chunks:
            logger.debug("no_unembedded_chunks")
            return 0

        total_embedded = 0
        for batch_start in range(0, len(chunks), self.batch_size):
            batch = chunks[batch_start : batch_start + self.batch_size]
            texts = [chunk.content for chunk in batch]

            try:
                embeddings = await self._generate_embeddings(texts)

                for chunk, embedding in zip(batch, embeddings):
                    chunk.embedding = embedding

                await db.flush()
                total_embedded += len(batch)

                logger.info(
                    "embedding_batch_complete",
                    batch_size=len(batch),
                    total_so_far=total_embedded,
                )

            except Exception as exc:
                logger.exception(
                    "embedding_batch_failed",
                    batch_start=batch_start,
                    batch_size=len(batch),
                    error=str(exc),
                )
                # Continue with next batch rather than failing entirely
                continue

        await db.commit()
        logger.info("embedding_run_complete", total_embedded=total_embedded)
        return total_embedded

    async def embed_single_chunk(
        self,
        db: AsyncSession,
        chunk_id: uuid.UUID,
    ) -> bool:
        """Generate and store an embedding for a single chunk.

        Returns ``True`` on success, ``False`` on failure.
        """
        result = await db.execute(select(DocumentChunk).where(DocumentChunk.id == chunk_id))
        chunk = result.scalar_one_or_none()
        if chunk is None:
            logger.error("chunk_not_found", chunk_id=str(chunk_id))
            return False

        try:
            embeddings = await self._generate_embeddings([chunk.content])
            chunk.embedding = embeddings[0]
            await db.commit()
            logger.info("single_chunk_embedded", chunk_id=str(chunk_id))
            return True
        except Exception as exc:
            logger.exception(
                "single_chunk_embedding_failed",
                chunk_id=str(chunk_id),
                error=str(exc),
            )
            return False

    async def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Call the configured embedding provider to generate vectors.

        Currently supports OpenAI.  Returns a list of embedding vectors,
        one per input text.
        """
        provider = self._settings.default_llm_provider

        if provider == "openai":
            return await self._openai_embeddings(texts)
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")

    async def _openai_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings via the OpenAI API.

        Uses the ``openai`` Python SDK with async support.
        """
        try:
            from openai import AsyncOpenAI

            api_key = (
                self._settings.openai_api_key.get_secret_value()
                if self._settings.openai_api_key
                else ""
            )
            client = AsyncOpenAI(api_key=api_key)

            response = await client.embeddings.create(
                model=self._settings.openai_embedding_model,
                input=texts,
            )

            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]

        except ImportError:
            logger.error("openai_not_installed")
            raise
        except Exception:
            logger.exception("openai_embedding_api_error")
            raise
