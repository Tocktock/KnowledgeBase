from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    pass


class DocumentStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("source_system", "source_external_id", name="uq_documents_source_external"),
        ForeignKeyConstraint(
            ["id", "current_revision_id"],
            ["document_revisions.document_id", "document_revisions.id"],
            name="fk_documents_current_revision_belongs_to_document",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    source_external_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    slug: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    language_code: Mapped[str] = mapped_column(String(12), nullable=False, server_default="ko")
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="knowledge")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=DocumentStatus.published.value)
    owner_team: Mapped[str | None] = mapped_column(Text(), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentRevision(Base):
    __tablename__ = "document_revisions"
    __table_args__ = (
        UniqueConstraint("document_id", "revision_number", name="uq_document_revision_number"),
        UniqueConstraint("document_id", "id", name="uq_document_revisions_document_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    source_revision_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    checksum: Mapped[str] = mapped_column(Text(), nullable=False)
    content_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    content_markdown: Mapped[str | None] = mapped_column(Text(), nullable=True)
    content_text: Mapped[str] = mapped_column(Text(), nullable=False)
    content_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    word_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("revision_id", "chunk_index", name="uq_document_chunk_revision_index"),
        ForeignKeyConstraint(
            ["document_id", "revision_id"],
            ["document_revisions.document_id", "document_revisions.id"],
            name="fk_document_chunks_revision_belongs_to_document",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            f"embedding_dimensions IS NULL OR embedding_dimensions = {settings.embedding_dimensions}",
            name="ck_document_chunks_embedding_dimensions_fixed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    heading_path: Mapped[list[str]] = mapped_column(ARRAY(Text()), nullable=False, server_default="{}")
    section_title: Mapped[str | None] = mapped_column(Text(), nullable=True)
    content_text: Mapped[str] = mapped_column(Text(), nullable=False)
    content_tokens: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    content_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('simple', coalesce(section_title, '') || ' ' || content_text)", persisted=True),
        nullable=True,
    )
    embedding: Mapped[list[float] | None] = mapped_column(VECTOR(settings.embedding_dimensions), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    embedding_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    __table_args__ = (
        UniqueConstraint("content_hash", "embedding_model", "embedding_dimensions", name="uq_embedding_cache_lookup"),
        CheckConstraint(
            f"embedding_dimensions = {settings.embedding_dimensions}",
            name="ck_embedding_cache_dimensions_fixed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    content_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer(), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    embedding: Mapped[list[float]] = mapped_column(VECTOR(settings.embedding_dimensions), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EmbeddingJob(Base):
    __tablename__ = "embedding_jobs"
    __table_args__ = (
        UniqueConstraint("revision_id", "embedding_model", "embedding_dimensions", name="uq_embedding_job_revision_model"),
        ForeignKeyConstraint(
            ["document_id", "revision_id"],
            ["document_revisions.document_id", "document_revisions.id"],
            name="fk_embedding_jobs_revision_belongs_to_document",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "status in ('queued', 'processing', 'completed', 'failed', 'cancelled')",
            name="ck_embedding_job_status",
        ),
        CheckConstraint(
            f"embedding_dimensions = {settings.embedding_dimensions}",
            name="ck_embedding_jobs_dimensions_fixed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=JobStatus.queued.value)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer(), nullable=False)
    batch_size: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="32")
    priority: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="100")
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentLink(Base):
    __tablename__ = "document_links"
    __table_args__ = (
        UniqueConstraint("source_revision_id", "link_order", name="uq_document_links_revision_order"),
        ForeignKeyConstraint(
            ["source_document_id", "source_revision_id"],
            ["document_revisions.document_id", "document_revisions.id"],
            name="fk_document_links_revision_belongs_to_document",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(target_slug) > 0", name="ck_document_links_target_slug_nonempty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    source_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    source_revision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="CASCADE"), nullable=False)
    target_slug: Mapped[str] = mapped_column(Text(), nullable=False)
    target_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    link_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    link_anchor: Mapped[str | None] = mapped_column(Text(), nullable=True)
    link_order: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SchemaMigration(Base):
    __tablename__ = "schema_migrations"

    version: Mapped[str] = mapped_column(Text(), primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
