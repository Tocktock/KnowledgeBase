from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
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


class DocumentVisibilityScope(str, enum.Enum):
    member_visible = "member_visible"
    evidence_only = "evidence_only"


class JobStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ConceptStatus(str, enum.Enum):
    suggested = "suggested"
    drafted = "drafted"
    approved = "approved"
    ignored = "ignored"
    stale = "stale"
    archived = "archived"


class GlossaryValidationState(str, enum.Enum):
    ok = "ok"
    needs_update = "needs_update"
    missing_draft = "missing_draft"
    stale_evidence = "stale_evidence"
    new_term = "new_term"


class VerificationState(str, enum.Enum):
    verified = "verified"
    monitoring = "monitoring"
    drift_detected = "drift_detected"
    evidence_insufficient = "evidence_insufficient"
    archived = "archived"


class ConceptType(str, enum.Enum):
    term = "term"
    product = "product"
    process = "process"
    team = "team"
    metric = "metric"
    entity = "entity"


class GlossaryJobKind(str, enum.Enum):
    refresh = "refresh"
    draft = "draft"
    validation_run = "validation_run"


class GlossaryJobScope(str, enum.Enum):
    full = "full"
    incremental = "incremental"
    term = "term"


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class UserRoleKind(str, enum.Enum):
    admin = "admin"
    member = "member"


class WorkspaceMembershipRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class ConnectorProvider(str, enum.Enum):
    google_drive = "google_drive"
    github = "github"
    notion = "notion"


class ConnectorOwnerScope(str, enum.Enum):
    workspace = "workspace"
    personal = "personal"


class ConnectorStatus(str, enum.Enum):
    active = "active"
    needs_reauth = "needs_reauth"
    revoked = "revoked"
    disconnected = "disconnected"


class ConnectorOAuthPurpose(str, enum.Enum):
    login = "login"
    connect_provider = "connect_provider"


class ConnectorResourceKind(str, enum.Enum):
    folder = "folder"
    shared_drive = "shared_drive"
    repository_docs = "repository_docs"
    repository_evidence = "repository_evidence"
    page = "page"
    database = "database"
    export_upload = "export_upload"


class ConnectorResourceStatus(str, enum.Enum):
    active = "active"
    paused = "paused"


class ConnectorSyncMode(str, enum.Enum):
    manual = "manual"
    auto = "auto"


class ConnectorSourceItemStatus(str, enum.Enum):
    imported = "imported"
    unchanged = "unchanged"
    unsupported = "unsupported"
    failed = "failed"
    deleted = "deleted"


class ConnectorSyncJobKind(str, enum.Enum):
    sync = "connector_sync"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_documents_workspace_slug"),
        ForeignKeyConstraint(
            ["id", "current_revision_id"],
            ["document_revisions.document_id", "document_revisions.id"],
            name="fk_documents_current_revision_belongs_to_document",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    source_external_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    slug: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    language_code: Mapped[str] = mapped_column(String(12), nullable=False, server_default="ko")
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="knowledge")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=DocumentStatus.published.value)
    visibility_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=DocumentVisibilityScope.member_visible.value,
    )
    owner_team: Mapped[str | None] = mapped_column(Text(), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    google_subject: Mapped[str | None] = mapped_column(Text(), nullable=True, unique=True)
    email: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)
    password_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=UserStatus.active.value)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token_hash: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    current_workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_roles_user_role"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    slug: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_memberships_workspace_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    invited_email: Mapped[str] = mapped_column(Text(), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    token_hash: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConnectorOAuthState(Base):
    __tablename__ = "connector_oauth_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    state: Mapped[str] = mapped_column(Text(), nullable=False, unique=True)
    purpose: Mapped[str] = mapped_column(String(30), nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    owner_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    code_verifier: Mapped[str] = mapped_column(Text(), nullable=False)
    return_path: Mapped[str] = mapped_column(Text(), nullable=False, server_default="/")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConnectorConnection(Base):
    __tablename__ = "connector_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    owner_scope: Mapped[str] = mapped_column(String(20), nullable=False)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    display_name: Mapped[str] = mapped_column(Text(), nullable=False)
    account_email: Mapped[str | None] = mapped_column(Text(), nullable=True)
    account_subject: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=ConnectorStatus.active.value)
    encrypted_access_token: Mapped[str] = mapped_column(Text(), nullable=False)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text(), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConnectorResource(Base):
    __tablename__ = "connector_resources"
    __table_args__ = (UniqueConstraint("connection_id", "resource_kind", "external_id", name="uq_connector_resource_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_connections.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str] = mapped_column(Text(), nullable=False)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    resource_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    parent_external_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    sync_children: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="true")
    visibility_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=DocumentVisibilityScope.member_visible.value,
    )
    selection_mode: Mapped[str] = mapped_column(String(30), nullable=False, server_default="browse")
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default=ConnectorSyncMode.manual.value)
    sync_interval_minutes: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=ConnectorResourceStatus.active.value)
    sync_cursor: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_auto_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConnectorSourceItem(Base):
    __tablename__ = "connector_source_items"
    __table_args__ = (UniqueConstraint("connection_id", "resource_id", "external_item_id", name="uq_connector_source_item_external"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_connections.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_resources.id", ondelete="CASCADE"), nullable=False)
    external_item_id: Mapped[str] = mapped_column(Text(), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(Text(), nullable=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_revision_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    internal_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    item_status: Mapped[str] = mapped_column(String(20), nullable=False)
    unsupported_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


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


class ConnectorSyncJob(Base):
    __tablename__ = "connector_sync_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    kind: Mapped[str] = mapped_column(String(30), nullable=False, server_default=ConnectorSyncJobKind.sync.value)
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_connections.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connector_resources.id", ondelete="CASCADE"), nullable=False)
    sync_mode: Mapped[str] = mapped_column(String(20), nullable=False, server_default=ConnectorSyncMode.manual.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=JobStatus.queued.value)
    priority: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="90")
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
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


class GlossaryVerificationPolicy(Base):
    __tablename__ = "glossary_verification_policies"
    __table_args__ = (
        UniqueConstraint("workspace_id", "label", "version", name="uq_glossary_verification_policy_workspace_label_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(Text(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="1")
    min_support_docs: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="2")
    freshness_sla_days: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="30")
    min_durable_sources: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="1")
    allow_evidence_only_support: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="true")
    continuous_revalidation_enabled: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="true")
    is_default: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KnowledgeConcept(Base):
    __tablename__ = "knowledge_concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    normalized_term: Mapped[str] = mapped_column(Text(), nullable=False)
    display_term: Mapped[str] = mapped_column(Text(), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    language_code: Mapped[str] = mapped_column(String(12), nullable=False, server_default="ko")
    concept_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default=ConceptType.term.value)
    confidence_score: Mapped[float] = mapped_column(nullable=False, server_default="0")
    support_doc_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    support_chunk_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=ConceptStatus.suggested.value)
    validation_state: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=GlossaryValidationState.new_term.value,
    )
    validation_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    evidence_signature: Mapped[str | None] = mapped_column(Text(), nullable=True)
    last_validation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("glossary_validation_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    verification_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("glossary_verification_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_state: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=VerificationState.evidence_insufficient.value,
    )
    verification_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    verification_policy_version: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    evidence_bundle_hash: Mapped[str | None] = mapped_column(Text(), nullable=True)
    owner_team_hint: Mapped[str | None] = mapped_column(Text(), nullable=True)
    source_system_mix: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    generated_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    canonical_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ConceptSupport(Base):
    __tablename__ = "concept_supports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_concepts.id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_revisions.id", ondelete="SET NULL"), nullable=True)
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    support_group_key: Mapped[str] = mapped_column(Text(), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_term: Mapped[str] = mapped_column(Text(), nullable=False)
    support_text: Mapped[str] = mapped_column(Text(), nullable=False)
    evidence_strength: Mapped[float] = mapped_column(nullable=False, server_default="0")
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GlossaryValidationRun(Base):
    __tablename__ = "glossary_validation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=JobStatus.queued.value)
    target_concept_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_concepts.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_scope: Mapped[str] = mapped_column(String(30), nullable=False, server_default="workspace_active")
    selected_resource_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    source_sync_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    validation_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    linked_job_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default="[]")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class GlossaryJob(Base):
    __tablename__ = "glossary_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False, server_default=GlossaryJobScope.full.value)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=JobStatus.queued.value)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_concept_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("knowledge_concepts.id", ondelete="SET NULL"), nullable=True)
    target_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    priority: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="200")
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


Index("ix_users_email", User.email)
Index("ix_user_sessions_user_id", UserSession.user_id)
Index("ix_user_sessions_current_workspace_id", UserSession.current_workspace_id)
Index("ix_workspaces_slug", Workspace.slug)
Index("ix_workspace_memberships_workspace_role", WorkspaceMembership.workspace_id, WorkspaceMembership.role)
Index("ix_workspace_memberships_user_id", WorkspaceMembership.user_id)
Index("ix_workspace_invitations_workspace_id", WorkspaceInvitation.workspace_id)
Index("ix_workspace_invitations_invited_email", WorkspaceInvitation.invited_email)
Index("ix_connector_oauth_states_expires_at", ConnectorOAuthState.expires_at)
Index("ix_connector_connections_workspace_scope", ConnectorConnection.workspace_id, ConnectorConnection.owner_scope, ConnectorConnection.owner_user_id)
Index("ix_connector_resources_connection_id", ConnectorResource.connection_id)
Index("ix_connector_resources_auto_due", ConnectorResource.sync_mode, ConnectorResource.next_auto_sync_at)
Index("ix_connector_resources_visibility_scope", ConnectorResource.visibility_scope)
Index("ix_connector_source_items_document_id", ConnectorSourceItem.internal_document_id)
Index("ix_connector_source_items_resource_status", ConnectorSourceItem.resource_id, ConnectorSourceItem.item_status)
Index("ix_connector_sync_jobs_status_priority_requested", ConnectorSyncJob.status, ConnectorSyncJob.priority, ConnectorSyncJob.requested_at)
Index("ix_documents_workspace_visibility", Document.workspace_id, Document.visibility_scope)
Index("ix_documents_visibility_scope", Document.visibility_scope)
Index(
    "uq_documents_workspace_source_external",
    Document.workspace_id,
    Document.source_system,
    Document.source_external_id,
    unique=True,
    postgresql_where=Document.source_external_id.is_not(None),
)
Index(
    "uq_knowledge_concepts_workspace_normalized_term",
    KnowledgeConcept.workspace_id,
    KnowledgeConcept.normalized_term,
    unique=True,
)
Index("ix_glossary_verification_policies_workspace_default", GlossaryVerificationPolicy.workspace_id, GlossaryVerificationPolicy.is_default)
Index("ix_knowledge_concepts_workspace_validation_state", KnowledgeConcept.workspace_id, KnowledgeConcept.validation_state, KnowledgeConcept.review_required)
Index("ix_knowledge_concepts_verification_state", KnowledgeConcept.workspace_id, KnowledgeConcept.verification_state)
Index("ix_glossary_validation_runs_workspace_requested", GlossaryValidationRun.workspace_id, GlossaryValidationRun.requested_at.desc())
Index("ix_glossary_jobs_status_priority_requested", GlossaryJob.status, GlossaryJob.priority, GlossaryJob.requested_at)
