"""Embedding generation using OpenAI text-embedding-3-small."""

from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from autonomocx.core.config import get_settings
from autonomocx.core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)

# Maximum batch size accepted by the API
_MAX_BATCH = 2048


class EmbeddingService:
    """Generate vector embeddings via OpenAI's embedding models."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(
            api_key=api_key
            or (settings.openai_api_key.get_secret_value() if settings.openai_api_key else None),
            timeout=settings.openai_timeout,
            max_retries=settings.openai_max_retries,
        )
        self._model = model or settings.openai_embedding_model
        self._dimensions = dimensions or settings.rag_embedding_dimensions

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string."""
        if not text or not text.strip():
            return [0.0] * self._dimensions

        try:
            response = await self._client.embeddings.create(
                input=text,
                model=self._model,
                dimensions=self._dimensions,
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("embedding_failed", model=self._model, error=str(exc))
            raise ExternalServiceError(
                f"Embedding generation failed: {exc}",
                error_code="EMBEDDING_ERROR",
            ) from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Automatically splits into sub-batches if needed to stay under
        the API's maximum batch size.
        """
        if not texts:
            return []

        # Filter out empty strings but track indices for re-assembly
        indexed: list[tuple[int, str]] = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not indexed:
            return [[0.0] * self._dimensions] * len(texts)

        all_embeddings: dict[int, list[float]] = {}

        # Process in sub-batches
        for batch_start in range(0, len(indexed), _MAX_BATCH):
            batch = indexed[batch_start : batch_start + _MAX_BATCH]
            batch_texts = [t for _, t in batch]

            try:
                response = await self._client.embeddings.create(
                    input=batch_texts,
                    model=self._model,
                    dimensions=self._dimensions,
                )
                for datum, (orig_idx, _) in zip(response.data, batch):
                    all_embeddings[orig_idx] = datum.embedding
            except Exception as exc:
                logger.error(
                    "embedding_batch_failed",
                    model=self._model,
                    batch_size=len(batch_texts),
                    error=str(exc),
                )
                raise ExternalServiceError(
                    f"Batch embedding generation failed: {exc}",
                    error_code="EMBEDDING_BATCH_ERROR",
                ) from exc

        # Re-assemble in original order, filling blanks with zero vectors
        zero = [0.0] * self._dimensions
        result: list[list[float]] = []
        for i in range(len(texts)):
            result.append(all_embeddings.get(i, zero))
        return result
