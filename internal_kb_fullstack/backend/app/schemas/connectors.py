from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ConnectorResourceSummary(BaseModel):
    id: UUID
    connection_id: UUID
    provider: str
    resource_kind: str
    external_id: str
    name: str
    resource_url: str | None = None
    parent_external_id: str | None = None
    visibility_scope: str
    selection_mode: str
    sync_children: bool
    sync_mode: str
    sync_interval_minutes: int | None = None
    status: str
    last_sync_started_at: datetime | None = None
    last_sync_completed_at: datetime | None = None
    next_auto_sync_at: datetime | None = None
    last_sync_summary: dict[str, Any] = Field(default_factory=dict)
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


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
    resources: list[ConnectorResourceSummary] = Field(default_factory=list)


class ConnectorBrowseItem(BaseModel):
    id: str
    name: str
    resource_kind: str
    resource_url: str | None = None
    parent_external_id: str | None = None
    has_children: bool = False
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorBrowseResponse(BaseModel):
    items: list[ConnectorBrowseItem] = Field(default_factory=list)
    kind: str | None = None
    parent_external_id: str | None = None
    cursor: str | None = None
    has_more: bool = False


class ConnectorSourceItemSummary(BaseModel):
    id: UUID
    resource_id: UUID
    external_item_id: str
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
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorListResponse(BaseModel):
    items: list[ConnectorConnectionSummary] = Field(default_factory=list)


class ConnectorProviderReadiness(BaseModel):
    provider: str
    oauth_configured: bool
    workspace_connection_exists: bool
    workspace_connection_status: str | None = None
    viewer_can_manage_workspace_connection: bool
    setup_state: str
    healthy_source_count: int = 0
    needs_attention_count: int = 0
    recommended_templates: list[str] = Field(default_factory=list)


class ConnectorReadinessResponse(BaseModel):
    providers: list[ConnectorProviderReadiness] = Field(default_factory=list)


class ConnectorResourceCreateRequest(BaseModel):
    resource_kind: str
    external_id: str
    name: str
    resource_url: str | None = None
    parent_external_id: str | None = None
    visibility_scope: str | None = None
    selection_mode: str | None = None
    sync_children: bool | None = None
    sync_mode: str | None = None
    sync_interval_minutes: int | None = None
    provider_metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorResourceUpdateRequest(BaseModel):
    visibility_scope: str | None = None
    selection_mode: str | None = None
    sync_children: bool | None = None
    sync_mode: str | None = None
    sync_interval_minutes: int | None = None
    status: str | None = None


class ConnectorUpdateRequest(BaseModel):
    display_name: str | None = None
    status: str | None = None


class ConnectorOAuthCallbackResponse(BaseModel):
    redirect_to: str
    connection: ConnectorConnectionSummary
