from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorTargetSummary(BaseModel):
    id: UUID
    connection_id: UUID
    target_type: str
    external_id: str
    name: str
    include_subfolders: bool
    sync_mode: str
    sync_interval_minutes: int | None = None
    status: str
    last_sync_started_at: datetime | None = None
    last_sync_completed_at: datetime | None = None
    next_auto_sync_at: datetime | None = None
    last_sync_summary: dict[str, Any] = Field(default_factory=dict)


class ConnectorConnectionSummary(BaseModel):
    id: UUID
    provider: str
    owner_scope: str
    owner_user_id: UUID | None = None
    display_name: str
    account_email: str | None = None
    account_subject: str
    status: str
    granted_scopes: list[str] = Field(default_factory=list)
    last_validated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    targets: list[ConnectorTargetSummary] = Field(default_factory=list)


class ConnectorBrowseItem(BaseModel):
    id: str
    name: str
    kind: str
    mime_type: str | None = None
    drive_id: str | None = None
    parent_id: str | None = None


class ConnectorBrowseResponse(BaseModel):
    items: list[ConnectorBrowseItem] = Field(default_factory=list)
    kind: str
    parent_id: str | None = None
    drive_id: str | None = None


class ConnectorSourceItemSummary(BaseModel):
    id: UUID
    target_id: UUID
    external_file_id: str
    mime_type: str | None = None
    name: str
    source_url: str | None = None
    source_revision_id: str | None = None
    internal_document_id: UUID | None = None
    item_status: str
    unsupported_reason: str | None = None
    error_message: str | None = None
    last_seen_at: datetime | None = None
    last_synced_at: datetime | None = None


class ConnectorListResponse(BaseModel):
    items: list[ConnectorConnectionSummary] = Field(default_factory=list)


class ConnectorReadinessResponse(BaseModel):
    oauth_configured: bool
    organization_connection_exists: bool
    organization_connection_status: str | None = None
    viewer_can_manage_org_connection: bool


class ConnectorTargetCreateRequest(BaseModel):
    target_type: str
    external_id: str
    name: str
    include_subfolders: bool = True
    sync_mode: str | None = None
    sync_interval_minutes: int | None = None


class ConnectorTargetUpdateRequest(BaseModel):
    include_subfolders: bool | None = None
    sync_mode: str | None = None
    sync_interval_minutes: int | None = None
    status: str | None = None


class ConnectorUpdateRequest(BaseModel):
    display_name: str | None = None
    status: str | None = None


class ConnectorOAuthCallbackResponse(BaseModel):
    redirect_to: str
    connection: ConnectorConnectionSummary
