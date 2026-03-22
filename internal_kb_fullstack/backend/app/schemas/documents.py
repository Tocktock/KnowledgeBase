from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.jobs import JobSummary


class IngestDocumentRequest(BaseModel):
    source_system: str = Field(..., examples=["notion", "repo", "manual"])
    source_external_id: str | None = None
    source_revision_id: str | None = None
    source_url: str | None = None
    slug: str | None = None
    title: str = Field(..., min_length=1)
    content_type: Literal["markdown", "text", "html"] = "markdown"
    content: str = Field(..., min_length=1)
    doc_type: str = "knowledge"
    language_code: str = "ko"
    owner_team: str | None = None
    status: Literal["draft", "published", "archived"] = "published"
    metadata: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    allow_slug_update: bool = True


class GenerateDefinitionDraftRequest(BaseModel):
    topic: str = Field(..., min_length=1)
    domain: str | None = None
    doc_type: str | None = None
    source_system: str | None = None
    owner_team: str | None = None
    reference_limit: int | None = Field(default=None, ge=3, le=12)
    search_limit: int | None = Field(default=None, ge=5, le=40)


class DefinitionDraftReference(BaseModel):
    index: int
    document_id: UUID
    document_title: str
    document_slug: str
    source_system: str
    source_url: str | None = None
    section_title: str | None = None
    heading_path: list[str] = Field(default_factory=list)
    excerpt: str


class GenerateDefinitionDraftResponse(BaseModel):
    title: str
    slug: str
    query: str
    markdown: str
    references: list[DefinitionDraftReference] = Field(default_factory=list)


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_system: str
    source_external_id: str | None = None
    source_url: str | None = None
    slug: str
    title: str = Field(..., min_length=1)
    language_code: str
    doc_type: str
    status: str
    owner_team: str | None = None
    metadata: dict[str, Any]
    current_revision_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    last_ingested_at: datetime | None = None


class RevisionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    revision_number: int
    source_revision_id: str | None = None
    checksum: str
    content_hash: str
    content_tokens: int
    word_count: int
    created_at: datetime


class ChunkSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    revision_id: UUID
    chunk_index: int
    heading_path: list[str]
    section_title: str | None = None
    content_tokens: int
    content_hash: str
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    embedding_generated_at: datetime | None = None


class HeadingSummary(BaseModel):
    title: str
    id: str


class IngestDocumentResponse(BaseModel):
    document: DocumentSummary
    revision: RevisionSummary
    job: JobSummary | None = None
    unchanged: bool = False


class DocumentDetailResponse(BaseModel):
    document: DocumentSummary
    revision: RevisionSummary | None = None
    chunks: list[ChunkSummary] = Field(default_factory=list)


class DocumentListItem(DocumentSummary):
    excerpt: str | None = None
    revision_number: int | None = None
    word_count: int | None = None
    content_tokens: int | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem] = Field(default_factory=list)
    total: int
    limit: int
    offset: int


class DocumentViewResponse(BaseModel):
    document: DocumentSummary
    revision: RevisionSummary | None = None
    content_markdown: str | None = None
    content_text: str | None = None
    headings: list[HeadingSummary] = Field(default_factory=list)
    linked_slugs: list[str] = Field(default_factory=list)
    chunks: list[ChunkSummary] = Field(default_factory=list)


class DocumentContentResponse(BaseModel):
    document_id: UUID
    revision_id: UUID
    content_markdown: str | None = None
    content_text: str


class DocumentRelationItem(BaseModel):
    id: UUID
    slug: str
    title: str
    excerpt: str | None = None
    owner_team: str | None = None
    doc_type: str
    updated_at: datetime


class DocumentRelationsResponse(BaseModel):
    outgoing: list[DocumentRelationItem] = Field(default_factory=list)
    backlinks: list[DocumentRelationItem] = Field(default_factory=list)
    related: list[DocumentRelationItem] = Field(default_factory=list)
