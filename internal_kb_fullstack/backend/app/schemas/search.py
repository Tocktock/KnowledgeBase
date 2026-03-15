from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    doc_type: str | None = None
    source_system: str | None = None
    owner_team: str | None = None
    include_debug_scores: bool = False


class SearchHit(BaseModel):
    chunk_id: UUID
    document_id: UUID
    revision_id: UUID
    document_title: str
    document_slug: str
    source_system: str
    source_url: str | None = None
    section_title: str | None = None
    heading_path: list[str]
    content_text: str
    hybrid_score: float
    vector_score: float | None = None
    keyword_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str = Field(..., min_length=1)
    hits: list[SearchHit]
