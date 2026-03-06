"""Shared / generic schemas used across the API."""

from __future__ import annotations

import enum
import math
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


# ---------------------------------------------------------------------------
# Generic paginated wrapper
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseModel, Generic[T]):
    """Envelope for paginated list endpoints."""

    items: list[T]
    total: int = Field(..., description="Total number of records matching the query")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
            }
        }
    )

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Convenience factory that computes ``total_pages`` automatically."""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if page_size else 0,
        )


# ---------------------------------------------------------------------------
# Standard response envelopes
# ---------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    """Returned on 4xx / 5xx errors."""

    detail: str = Field(..., description="Human-readable error message")
    error_code: Optional[str] = Field(
        None, description="Machine-readable error code (e.g. 'INVALID_CREDENTIALS')"
    )
    request_id: Optional[str] = Field(
        None, description="Correlation ID for tracing the request"
    )


class SuccessResponse(BaseModel):
    """Generic success envelope for non-resource responses."""

    message: str = Field(..., description="Human-readable success message")
    data: Optional[Any] = Field(None, description="Optional payload")
