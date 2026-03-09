"""Background task entry point for document ingestion.

This module provides a standalone function suitable for
``FastAPI.BackgroundTasks.add_task()``.  It creates its own database
session so the request session is not held open during long-running
processing.
"""

from __future__ import annotations

import uuid

import structlog

from autonomocx.core.database import async_session_factory
from autonomocx.workers.document_processor import DocumentProcessor

logger = structlog.get_logger(__name__)


async def process_document_background(document_id: uuid.UUID) -> None:
    """Process a single document in the background.

    Creates a fresh database session and runs the full pipeline:
    extract → chunk → embed → persist.
    """
    logger.info("background_ingestion_started", document_id=str(document_id))

    processor = DocumentProcessor()
    session_factory = async_session_factory()

    async with session_factory() as session:
        try:
            await processor.process_document(session, document_id)
        except Exception:
            logger.exception(
                "background_ingestion_unhandled",
                document_id=str(document_id),
            )
