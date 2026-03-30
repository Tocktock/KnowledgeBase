from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.documents import DocumentListItem
from app.schemas.glossary import GlossaryConceptSummary, GlossaryValidationRunSummary
from app.schemas.jobs import JobSummary


class WorkspaceSummary(BaseModel):
    id: UUID
    slug: str
    name: str
    is_default: bool


class WorkspaceContextResponse(BaseModel):
    workspace: WorkspaceSummary | None = None
    role: str | None = None
    can_manage_connectors: bool = False


class WorkspaceMemberSummary(BaseModel):
    user_id: UUID
    email: str
    name: str
    avatar_url: str | None = None
    role: str
    created_at: datetime


class WorkspaceInvitationSummary(BaseModel):
    id: UUID
    workspace_id: UUID
    invited_email: str
    role: str
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime


class WorkspaceInvitationCreateRequest(BaseModel):
    invited_email: str
    role: str


class WorkspaceInvitationCreateResponse(BaseModel):
    invitation: WorkspaceInvitationSummary
    invite_url: str


class WorkspaceInvitationAcceptResponse(BaseModel):
    workspace: WorkspaceSummary
    role: str


class WorkspaceInvitationPreviewResponse(BaseModel):
    invited_email: str
    workspace: WorkspaceSummary
    role: str
    expires_at: datetime
    accepted_at: datetime | None = None
    is_expired: bool
    local_password_exists: bool


class WorkspaceSourceHealthSummary(BaseModel):
    workspace_connection_count: int = 0
    healthy_source_count: int = 0
    needs_attention_count: int = 0
    providers_needing_attention: list[str] = Field(default_factory=list)


class WorkspaceOverviewResponse(BaseModel):
    authenticated: bool = False
    workspace: WorkspaceSummary | None = None
    viewer_role: str | None = None
    can_manage_connectors: bool = False
    setup_state: str = "anonymous"
    next_actions: list[str] = Field(default_factory=list)
    source_health: WorkspaceSourceHealthSummary = Field(default_factory=WorkspaceSourceHealthSummary)
    featured_docs: list[DocumentListItem] = Field(default_factory=list)
    featured_concepts: list[GlossaryConceptSummary] = Field(default_factory=list)
    recent_sync_issues: list[JobSummary] = Field(default_factory=list)
    latest_validation_run: GlossaryValidationRunSummary | None = None
    review_required_count: int = 0
    verification_counts: dict[str, int] = Field(default_factory=dict)
