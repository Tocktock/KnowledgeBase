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
    result_type: str = "document"
    matched_concept_id: UUID | None = None
    matched_concept_term: str | None = None
    evidence_kind: str | None = None
    evidence_strength: float | None = None
    support_group_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str = Field(..., min_length=1)
    resolved_concept_id: UUID | None = None
    resolved_concept_term: str | None = None
    weak_grounding: bool = False
    notes: list[str] = Field(default_factory=list)
    hits: list[SearchHit]


class SearchExplainResponse(SearchResponse):
    normalized_query: str
    resolved_concept_status: str | None = None
    canonical_document_slug: str | None = None
