"""Knowledge base & document schemas."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DocumentStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Knowledge base requests
# ---------------------------------------------------------------------------


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    embedding_model: str = Field(default="text-embedding-3-small", max_length=128)
    chunk_size: int = Field(default=512, ge=64, le=8192)
    chunk_overlap: int = Field(default=64, ge=0, le=4096)


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    chunk_size: int | None = Field(None, ge=64, le=8192)
    chunk_overlap: int | None = Field(None, ge=0, le=4096)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Knowledge base responses
# ---------------------------------------------------------------------------


class KnowledgeBaseResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    description: str | None = None
    embedding_model: str
    chunk_size: int
    chunk_overlap: int
    document_count: int
    total_chunks: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Document responses
# ---------------------------------------------------------------------------


class DocumentResponse(BaseModel):
    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    title: str
    source_url: str | None = None
    file_type: str | None = None
    file_size_bytes: int | None = None
    chunk_count: int
    status: DocumentStatus
    error_message: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    knowledge_base_ids: list[uuid.UUID] = Field(
        ..., min_length=1, description="IDs of knowledge bases to search"
    )
    top_k: int = Field(default=5, ge=1, le=100)


class SearchResult(BaseModel):
    chunk_content: str
    document_title: str
    score: float = Field(..., description="Similarity score (higher is better)")
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query_time_ms: float = Field(..., description="Search latency in milliseconds")
