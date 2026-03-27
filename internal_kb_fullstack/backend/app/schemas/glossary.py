from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.trust import TrustSummary


class GlossaryConceptDocumentLink(BaseModel):
    id: UUID
    slug: str
    title: str
    status: str
    doc_type: str
    owner_team: str | None = None


class GlossaryConceptSummary(BaseModel):
    id: UUID
    slug: str
    normalized_term: str
    display_term: str
    aliases: list[str] = Field(default_factory=list)
    language_code: str
    concept_type: str
    confidence_score: float
    support_doc_count: int
    support_chunk_count: int
    status: str
    owner_team_hint: str | None = None
    source_system_mix: list[str] = Field(default_factory=list)
    generated_document: GlossaryConceptDocumentLink | None = None
    canonical_document: GlossaryConceptDocumentLink | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    refreshed_at: datetime
    updated_at: datetime
    trust: TrustSummary


class GlossarySupportItem(BaseModel):
    id: UUID
    document_id: UUID
    document_slug: str
    document_title: str
    document_status: str
    document_doc_type: str
    owner_team: str | None = None
    revision_id: UUID | None = None
    chunk_id: UUID | None = None
    evidence_kind: str
    evidence_term: str
    evidence_strength: float
    support_group_key: str
    support_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    trust: TrustSummary


class GlossaryConceptDetailResponse(BaseModel):
    concept: GlossaryConceptSummary
    supports: list[GlossarySupportItem] = Field(default_factory=list)
    related_concepts: list[GlossaryConceptSummary] = Field(default_factory=list)


class GlossaryConceptListResponse(BaseModel):
    items: list[GlossaryConceptSummary] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class GlossaryRefreshRequest(BaseModel):
    scope: Literal["full", "incremental"] = "full"


class GlossaryConceptUpdateRequest(BaseModel):
    action: Literal["approve", "ignore", "mark_stale", "suggest", "merge", "split"]
    canonical_document_id: UUID | None = None
    merge_into_concept_id: UUID | None = None
    split_aliases: list[str] = Field(default_factory=list)


class GlossaryDraftRequest(BaseModel):
    domain: str | None = None
    regenerate: bool = True
