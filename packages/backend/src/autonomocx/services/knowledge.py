"""Knowledge base and document management service.

Exposes functions matching the signatures expected by
``autonomocx.api.v1.knowledge``.
"""

from __future__ import annotations

import hashlib
import math
import uuid
from typing import Any

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.exceptions import ValidationError
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
    *,
    org_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
) -> dict[str, Any]:
    """Return paginated knowledge bases for *org_id*.

    Returns ``{"items": [...], "total": int, "pages": int}``.
    """
    filters = [KnowledgeBase.org_id == org_id]
    if is_active is not None:
        filters.append(KnowledgeBase.is_active == is_active)

    # Total count
    count_stmt = select(func.count()).select_from(KnowledgeBase).where(*filters)
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Paginated rows
    offset = (page - 1) * page_size
    stmt = (
        select(KnowledgeBase)
        .where(*filters)
        .order_by(KnowledgeBase.name)
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "pages": math.ceil(total / page_size) if page_size else 0,
    }


async def create_knowledge_base(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    name: str,
    description: str | None = None,
    embedding_model: str | None = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    metadata: dict[str, Any] | None = None,
) -> KnowledgeBase:
    """Create a new knowledge base."""
    kb = KnowledgeBase(
        org_id=org_id,
        name=name,
        description=description,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        is_active=True,
        document_count=0,
        total_chunks=0,
    )
    if metadata is not None:
        kb.metadata_ = metadata  # type: ignore[attr-defined]
    db.add(kb)
    await db.flush()

    logger.info("knowledge_base_created", kb_id=str(kb.id), name=kb.name)
    return kb


async def get_knowledge_base(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    org_id: uuid.UUID,
) -> KnowledgeBase | None:
    """Return a single knowledge base scoped to *org_id*, or ``None``."""
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def update_knowledge_base(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    org_id: uuid.UUID,
    data: dict[str, Any],
) -> KnowledgeBase | None:
    """Partially update a knowledge base. Returns ``None`` if not found."""
    kb = await get_knowledge_base(db, kb_id=kb_id, org_id=org_id)
    if kb is None:
        return None

    for field in (
        "name",
        "description",
        "embedding_model",
        "chunk_size",
        "chunk_overlap",
        "is_active",
        "metadata",
    ):
        if field in data and data[field] is not None:
            attr = "metadata_" if field == "metadata" else field
            setattr(kb, attr, data[field])

    db.add(kb)
    await db.flush()

    logger.info("knowledge_base_updated", kb_id=str(kb.id))
    return kb


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


async def get_kb_documents(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Return paginated documents within a knowledge base.

    Returns ``{"items": [...], "total": int, "pages": int}``.
    """
    filters = [Document.knowledge_base_id == kb_id]

    count_stmt = select(func.count()).select_from(Document).where(*filters)
    total: int = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = list(result.scalars().all())

    return {
        "items": items,
        "total": total,
        "pages": math.ceil(total / page_size) if page_size else 0,
    }


async def upload_document(
    db: AsyncSession,
    *,
    kb_id: uuid.UUID,
    org_id: uuid.UUID,
    filename: str,
    content_type: str | None,
    file: Any,
) -> Document:
    """Persist document metadata and queue it for async processing.

    The actual file is saved to object storage (S3/local) by the caller
    or a background task.  This service layer records the metadata row
    with status PENDING so the ingestion worker picks it up.
    """
    # Verify KB exists and belongs to org
    kb = await get_knowledge_base(db, kb_id=kb_id, org_id=org_id)
    if kb is None:
        raise ValidationError(f"Knowledge base {kb_id} not found for this organization.")

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

    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

    doc = Document(
        knowledge_base_id=kb_id,
        title=filename,
        source_type="upload",
        file_path=None,  # populated after S3 upload
        file_type=file_ext,
        file_size_bytes=len(content_bytes) if content_bytes else 0,
        content_hash=content_hash,
        status=DocumentStatus.PENDING,
        chunk_count=0,
        version=1,
        metadata_={
            "original_filename": filename,
            "content_type": content_type or "application/octet-stream",
        },
    )
    # Expose filename / content_type as attributes for Pydantic from_attributes
    doc.filename = filename  # type: ignore[attr-defined]
    doc.content_type = content_type  # type: ignore[attr-defined]

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
    *,
    kb_id: uuid.UUID,
    doc_id: uuid.UUID,
    org_id: uuid.UUID,
) -> bool:
    """Delete a document and its associated chunks.

    Returns ``True`` if deleted, ``False`` if not found.
    Also decrements the parent knowledge base counters.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.knowledge_base_id == kb_id,
        )
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        return False

    # Verify KB belongs to org
    kb = await get_knowledge_base(db, kb_id=kb_id, org_id=org_id)
    if kb is None:
        return False

    chunk_count = doc.chunk_count

    # Delete chunks first
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_id))

    # Delete document
    await db.delete(doc)
    await db.flush()

    # Update kb counters
    kb.document_count = max(0, kb.document_count - 1)
    kb.total_chunks = max(0, kb.total_chunks - chunk_count)
    db.add(kb)
    await db.flush()

    logger.info("document_deleted", doc_id=str(doc_id), kb_id=str(kb_id))
    return True


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------


async def search_knowledge(
    db: AsyncSession,
    *,
    org_id: uuid.UUID,
    query: str,
    knowledge_base_ids: list[uuid.UUID] | None = None,
    top_k: int = 5,
    similarity_threshold: float = 0.72,
) -> dict[str, Any]:
    """Search across knowledge bases using vector similarity.

    Returns a dict with ``results`` and ``total_results`` keys.

    NOTE: Full vector search requires the embedding pipeline (OpenAI /
    pgvector).  This implementation provides the query interface; the
    actual embedding + cosine-similarity search is wired up once the
    AI pipeline package is connected.
    """
    # Determine which KBs to search
    if knowledge_base_ids:
        kb_stmt = select(KnowledgeBase).where(
            KnowledgeBase.id.in_(knowledge_base_ids),
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
        return {"results": [], "total_results": 0}

    target_kb_ids = [kb.id for kb in knowledge_bases]

    # TODO: Replace with actual pgvector cosine similarity search:
    #   1. Generate embedding for `query` via OpenAI / embedding model
    #   2. SELECT chunks ORDER BY embedding <=> query_embedding LIMIT top_k
    #   3. Filter by similarity_threshold
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

    # Fetch parent documents for filename lookup
    doc_ids = {c.document_id for c in chunks}
    doc_map: dict[uuid.UUID, Document] = {}
    if doc_ids:
        doc_result = await db.execute(
            select(Document).where(Document.id.in_(doc_ids))
        )
        for d in doc_result.scalars().all():
            doc_map[d.id] = d

    results = [
        {
            "document_id": c.document_id,
            "knowledge_base_id": c.knowledge_base_id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "similarity_score": 0.0,  # populated when vector search is active
            "document_filename": doc_map[c.document_id].title
            if c.document_id in doc_map
            else "unknown",
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
        "results": results,
        "total_results": len(results),
    }
