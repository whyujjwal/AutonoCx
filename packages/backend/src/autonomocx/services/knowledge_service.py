"""Knowledge base and document management service."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import NotFoundError, ValidationError
from autonomocx.models.knowledge import (
    Document,
    DocumentChunk,
    DocumentStatus,
    KnowledgeBase,
)

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------


async def list_knowledge_bases(
    db: AsyncSession,
    org_id: uuid.UUID,
) -> list[KnowledgeBase]:
    """Return all knowledge bases for *org_id*."""
    stmt = select(KnowledgeBase).where(KnowledgeBase.org_id == org_id).order_by(KnowledgeBase.name)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_knowledge_base(
    db: AsyncSession,
    org_id: uuid.UUID,
    data: dict,
) -> KnowledgeBase:
    """Create a new knowledge base."""
    kb = KnowledgeBase(
        org_id=org_id,
        name=data["name"],
        description=data.get("description"),
        embedding_model=data.get("embedding_model"),
        chunk_size=data.get("chunk_size", 512),
        chunk_overlap=data.get("chunk_overlap", 64),
        is_active=data.get("is_active", True),
        document_count=0,
        total_chunks=0,
    )
    db.add(kb)
    await db.flush()

    logger.info("knowledge_base_created", kb_id=str(kb.id), name=kb.name)
    return kb


async def get_knowledge_base(
    db: AsyncSession,
    kb_id: uuid.UUID,
) -> KnowledgeBase:
    """Return a single knowledge base.  Raises ``NotFoundError`` if missing."""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = result.scalar_one_or_none()
    if kb is None:
        raise NotFoundError(f"Knowledge base {kb_id} not found.")
    return kb


async def update_knowledge_base(
    db: AsyncSession,
    kb_id: uuid.UUID,
    data: dict,
) -> KnowledgeBase:
    """Partially update a knowledge base."""
    kb = await get_knowledge_base(db, kb_id)

    for field in (
        "name",
        "description",
        "embedding_model",
        "chunk_size",
        "chunk_overlap",
        "is_active",
    ):
        if field in data and data[field] is not None:
            setattr(kb, field, data[field])

    db.add(kb)
    await db.flush()

    logger.info("knowledge_base_updated", kb_id=str(kb.id))
    return kb


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


async def list_documents(
    db: AsyncSession,
    kb_id: uuid.UUID,
) -> list[Document]:
    """Return all documents in a knowledge base."""
    stmt = (
        select(Document)
        .where(Document.knowledge_base_id == kb_id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upload_document(
    db: AsyncSession,
    kb_id: uuid.UUID,
    file: Any,  # UploadFile from FastAPI
) -> Document:
    """Persist document metadata and queue it for async processing.

    The actual file is saved to object storage (S3/local) by the caller
    or a background task.  This service layer records the metadata row
    with status PENDING so the ingestion worker picks it up.
    """
    kb = await get_knowledge_base(db, kb_id)

    # Read file content for hashing (assumes small-to-medium files)
    content_bytes: bytes = b""
    if hasattr(file, "read"):
        content_bytes = await file.read()
        await file.seek(0)  # reset for downstream consumers

    content_hash = hashlib.sha256(content_bytes).hexdigest() if content_bytes else None

    # Check for duplicate content
    if content_hash:
        dup = await db.execute(
            select(Document).where(
                Document.knowledge_base_id == kb_id,
                Document.content_hash == content_hash,
            )
        )
        if dup.scalar_one_or_none() is not None:
            raise ValidationError("A document with identical content already exists.")

    filename = getattr(file, "filename", "untitled")
    content_type = getattr(file, "content_type", "application/octet-stream")
    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

    doc = Document(
        knowledge_base_id=kb_id,
        title=filename,
        source_type="upload",
        file_path=None,  # populated after S3 upload
        file_type=file_ext,
        file_size_bytes=len(content_bytes) if content_bytes else None,
        content_hash=content_hash,
        status=DocumentStatus.PENDING,
        chunk_count=0,
        version=1,
        metadata_={"original_filename": filename, "content_type": content_type},
    )
    db.add(doc)
    await db.flush()

    # Update kb document_count
    kb.document_count += 1
    db.add(kb)
    await db.flush()

    logger.info(
        "document_uploaded",
        doc_id=str(doc.id),
        kb_id=str(kb_id),
        filename=filename,
        size=len(content_bytes) if content_bytes else 0,
    )
    return doc


async def delete_document(
    db: AsyncSession,
    doc_id: uuid.UUID,
) -> None:
    """Delete a document and its associated chunks.

    Also decrements the parent knowledge base counters.
    """
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found.")

    kb_id = doc.knowledge_base_id
    chunk_count = doc.chunk_count

    # Delete chunks first
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))

    # Delete document
    await db.delete(doc)
    await db.flush()

    # Update kb counters
    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    kb = kb_result.scalar_one_or_none()
    if kb is not None:
        kb.document_count = max(0, kb.document_count - 1)
        kb.total_chunks = max(0, kb.total_chunks - chunk_count)
        db.add(kb)
        await db.flush()

    logger.info("document_deleted", doc_id=str(doc_id), kb_id=str(kb_id))


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


async def search_knowledge(
    db: AsyncSession,
    org_id: uuid.UUID,
    query: str,
    kb_ids: list[uuid.UUID] | None = None,
    top_k: int = 5,
) -> dict[str, Any]:
    """Search across knowledge bases using vector similarity.

    Returns a ``SearchResponse``-compatible dict with ranked results.

    NOTE: Full vector search requires the embedding pipeline (OpenAI /
    pgvector).  This implementation provides the query interface; the
    actual embedding + cosine-similarity search is wired up once the
    AI pipeline package is connected.
    """
    # Determine which KBs to search
    if kb_ids:
        kb_stmt = select(KnowledgeBase).where(
            KnowledgeBase.id.in_(kb_ids),
            KnowledgeBase.org_id == org_id,
            KnowledgeBase.is_active.is_(True),
        )
    else:
        kb_stmt = select(KnowledgeBase).where(
            KnowledgeBase.org_id == org_id,
            KnowledgeBase.is_active.is_(True),
        )

    kb_result = await db.execute(kb_stmt)
    knowledge_bases = kb_result.scalars().all()

    if not knowledge_bases:
        return {"query": query, "results": [], "total": 0}

    target_kb_ids = [kb.id for kb in knowledge_bases]

    # TODO: Replace with actual pgvector cosine similarity search:
    #   1. Generate embedding for `query` via OpenAI / embedding model
    #   2. SELECT chunks ORDER BY embedding <=> query_embedding LIMIT top_k
    #
    # Fallback: simple text ILIKE search until embeddings are wired up.
    pattern = f"%{query}%"
    chunk_stmt = (
        select(DocumentChunk)
        .where(
            DocumentChunk.knowledge_base_id.in_(target_kb_ids),
            DocumentChunk.content.ilike(pattern),
        )
        .limit(top_k)
    )
    chunk_result = await db.execute(chunk_stmt)
    chunks = chunk_result.scalars().all()

    results = [
        {
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "knowledge_base_id": str(c.knowledge_base_id),
            "content": c.content,
            "chunk_index": c.chunk_index,
            "score": None,  # populated when vector search is active
            "metadata": c.metadata_,
        }
        for c in chunks
    ]

    logger.info(
        "knowledge_searched",
        org_id=str(org_id),
        query_len=len(query),
        results_count=len(results),
    )

    return {
        "query": query,
        "results": results,
        "total": len(results),
    }
