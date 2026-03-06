"""Knowledge base management, document upload, and semantic search endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from autonomocx.core.database import get_db
from autonomocx.core.dependencies import get_current_user, require_role
from autonomocx.models.user import User, UserRole
from autonomocx.services.knowledge import (
    create_knowledge_base,
    delete_document,
    get_kb_documents,
    get_knowledge_base,
    list_knowledge_bases,
    search_knowledge,
    update_knowledge_base,
    upload_document,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class KnowledgeBaseOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    description: str | None = None
    embedding_model: str | None = None
    chunk_size: int
    chunk_overlap: int
    document_count: int
    total_chunks: int
    is_active: bool
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    embedding_model: str | None = Field(None, max_length=128)
    chunk_size: int = Field(512, ge=64, le=4096)
    chunk_overlap: int = Field(64, ge=0, le=512)
    metadata: dict[str, Any] | None = None


class KnowledgeBaseUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    embedding_model: str | None = Field(None, max_length=128)
    chunk_size: int | None = Field(None, ge=64, le=4096)
    chunk_overlap: int | None = Field(None, ge=0, le=512)
    is_active: bool | None = None
    metadata: dict[str, Any] | None = None


class DocumentOut(BaseModel):
    id: UUID
    knowledge_base_id: UUID
    filename: str
    content_type: str | None = None
    file_size_bytes: int
    chunk_count: int
    status: str
    error_message: str | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    knowledge_base_ids: list[UUID] | None = Field(
        None, description="Filter to specific KBs (null = search all)"
    )
    top_k: int = Field(5, ge=1, le=50)
    similarity_threshold: float = Field(0.72, ge=0.0, le=1.0)


class SearchResultItem(BaseModel):
    document_id: UUID
    knowledge_base_id: UUID
    chunk_index: int
    content: str
    similarity_score: float
    document_filename: str
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_results: int


class PaginatedKnowledgeBases(BaseModel):
    items: list[KnowledgeBaseOut]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedDocuments(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    detail: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=PaginatedKnowledgeBases,
    summary="List knowledge bases",
)
async def list_kbs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedKnowledgeBases:
    """Return paginated knowledge bases for the current organization."""
    result = await list_knowledge_bases(
        db,
        org_id=current_user.org_id,
        page=page,
        page_size=page_size,
        is_active=is_active,
    )
    return PaginatedKnowledgeBases(
        items=[KnowledgeBaseOut.model_validate(kb) for kb in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.post(
    "/",
    response_model=KnowledgeBaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a knowledge base",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def create_kb(
    body: KnowledgeBaseCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    """Create a new knowledge base. Requires ADMIN or DEVELOPER role."""
    kb = await create_knowledge_base(
        db,
        org_id=current_user.org_id,
        name=body.name,
        description=body.description,
        embedding_model=body.embedding_model,
        chunk_size=body.chunk_size,
        chunk_overlap=body.chunk_overlap,
        metadata=body.metadata,
    )
    return KnowledgeBaseOut.model_validate(kb)


@router.get(
    "/{kb_id}",
    response_model=KnowledgeBaseOut,
    summary="Get knowledge base",
)
async def get_kb(
    kb_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    """Return a specific knowledge base."""
    kb = await get_knowledge_base(db, kb_id=kb_id, org_id=current_user.org_id)
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return KnowledgeBaseOut.model_validate(kb)


@router.put(
    "/{kb_id}",
    response_model=KnowledgeBaseOut,
    summary="Update knowledge base",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def update_kb(
    kb_id: UUID,
    body: KnowledgeBaseUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseOut:
    """Update a knowledge base configuration. Requires ADMIN or DEVELOPER role."""
    kb = await update_knowledge_base(
        db,
        kb_id=kb_id,
        org_id=current_user.org_id,
        data=body.model_dump(exclude_unset=True),
    )
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return KnowledgeBaseOut.model_validate(kb)


@router.get(
    "/{kb_id}/documents",
    response_model=PaginatedDocuments,
    summary="List documents in knowledge base",
)
async def list_documents(
    kb_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedDocuments:
    """Return paginated documents within a knowledge base."""
    # Verify KB exists and belongs to org
    kb = await get_knowledge_base(db, kb_id=kb_id, org_id=current_user.org_id)
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    result = await get_kb_documents(
        db,
        kb_id=kb_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedDocuments(
        items=[DocumentOut.model_validate(d) for d in result["items"]],
        total=result["total"],
        page=page,
        page_size=page_size,
        pages=result["pages"],
    )


@router.post(
    "/{kb_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def upload_doc(
    kb_id: UUID,
    file: UploadFile = File(..., description="Document file to upload"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DocumentOut:
    """Upload a document to a knowledge base for processing and indexing.

    Supported formats: PDF, TXT, DOCX, MD, CSV, JSON.
    The document will be chunked and embedded asynchronously.
    """
    # Verify KB exists and belongs to org
    kb = await get_knowledge_base(db, kb_id=kb_id, org_id=current_user.org_id)
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    # Validate file type
    allowed_types = {
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/json",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Supported: PDF, TXT, DOCX, MD, CSV, JSON",
        )

    doc = await upload_document(
        db,
        kb_id=kb_id,
        org_id=current_user.org_id,
        filename=file.filename or "unnamed",
        content_type=file.content_type,
        file=file,
    )
    return DocumentOut.model_validate(doc)


@router.delete(
    "/{kb_id}/documents/{doc_id}",
    response_model=MessageResponse,
    summary="Remove a document",
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.DEVELOPER))],
)
async def remove_document(
    kb_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Remove a document from a knowledge base and delete its embeddings."""
    success = await delete_document(
        db,
        kb_id=kb_id,
        doc_id=doc_id,
        org_id=current_user.org_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return MessageResponse(detail="Document removed")


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across knowledge bases",
)
async def semantic_search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    """Perform semantic search across knowledge bases using vector similarity."""
    results = await search_knowledge(
        db,
        org_id=current_user.org_id,
        query=body.query,
        knowledge_base_ids=body.knowledge_base_ids,
        top_k=body.top_k,
        similarity_threshold=body.similarity_threshold,
    )
    return SearchResponse(
        query=body.query,
        results=[SearchResultItem(**r) for r in results["results"]],
        total_results=results["total_results"],
    )
