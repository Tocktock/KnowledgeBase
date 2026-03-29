# Connector Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/connectors.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend page

### `GET /connectors`

- Purpose: role-aware source overview and source status surface.
- Caller:
  - anonymous: marketing and login continuation view
  - member: read-only workspace status plus optional personal section
  - owner/admin: overview plus entry points into setup/detail pages
- Response: HTML page rendered by the frontend app.

### `GET /connectors/setup/[provider]`

- Purpose: dedicated provider setup page for OAuth continuation, browse/search/upload, and resource creation.
- Caller:
  - anonymous: login continuation entry
  - member: read-only or blocked for workspace scope
  - owner/admin: full setup UI for workspace scope
- Query params:
  - `scope=workspace|personal`
  - `template`
  - optional `connectionId`
- Response: HTML page rendered by the frontend app.

### `GET /connectors/[connectionId]`

- Purpose: dedicated connection detail page for one connection’s resources, status, and management actions.
- Caller: authenticated user with scope-appropriate visibility of the connection.
- Response: HTML page rendered by the frontend app.

## Backend readiness and connection APIs

### `GET /v1/connectors/readiness`

- Purpose: summarize provider readiness and recommended setup templates.
- Caller: anonymous or authenticated user.
- Response model: list of `ConnectorProviderReadiness`
- Important fields:
  - `provider`
  - `oauth_configured`
  - `workspace_connection_exists`
  - `workspace_connection_status`
  - `viewer_can_manage_workspace_connection`
  - `setup_state`
  - `healthy_source_count`
  - `needs_attention_count`
  - `recommended_templates`

### `GET /v1/connectors`

- Purpose: list connector connections by ownership scope.
- Caller: authenticated user.
- Query parameters:
  - `scope=workspace|personal`
- Response model: connection list defined in `connectors.py`

### `POST /v1/connectors/{provider}/oauth/start`

- Purpose: start provider OAuth for a connector provider.
- Caller: authenticated user or anonymous user routed through login continuation.
- Query parameters:
  - `scope`
  - `return_to`
  - optional provider-specific continuation values
- Response shape: redirect response to provider OAuth or to `/login` when authentication is required.
- Important error states:
  - unknown provider
  - provider not configured
  - insufficient role for workspace scope

### `GET /v1/connectors/{provider}/oauth/callback`

- Purpose: complete provider OAuth and create or update a connector connection.
- Caller: provider callback.
- Response shape: redirect or JSON payload used by the frontend continuation flow.
- Important error states:
  - invalid provider
  - callback exchange failure
  - scope mismatch

### `GET /v1/connectors/{connection_id}`

- Purpose: fetch one connector connection detail.
- Caller: connection owner or workspace admin/member according to scope.
- Response model: connector connection detail shape defined in `connectors.py`

### `PATCH /v1/connectors/{connection_id}`

- Purpose: update connection-level metadata such as label or scope-specific settings exposed by the API.
- Caller:
  - workspace scope: `owner` or `admin`
  - personal scope: owning user
- Request model: connection update request from `connectors.py`

### `DELETE /v1/connectors/{connection_id}`

- Purpose: delete a connector connection and its managed resources.
- Caller:
  - workspace scope: `owner` or `admin`
  - personal scope: owning user
- Important error states:
  - unauthorized caller
  - missing connection

## Browse and resource APIs

### `GET /v1/connectors/{connection_id}/browse`

- Purpose: browse or search provider resources before source creation.
- Caller:
  - workspace scope: `owner` or `admin`
  - personal scope: owning user
- Query parameters:
  - provider-specific query or cursor fields
  - optional template and selection context
- Response model: browse result list from `connectors.py`
- Important behavior:
  - GitHub returns repository items with `resource_kind` matching the selected template
  - Notion and Drive return provider-native browse/search results normalized into connector browse items

### `GET /v1/connectors/{connection_id}/resources`

- Purpose: list managed resources under a connection.
- Caller: same access rules as connection detail.
- Response model: list of `ConnectorResourceSummary`

### `POST /v1/connectors/{connection_id}/resources`

- Purpose: create a managed resource from a selected provider item.
- Caller:
  - workspace scope: `owner` or `admin`
  - personal scope: owning user
- Request model: `ConnectorResourceCreateRequest`
- Important fields:
  - `resource_kind`
  - `external_id`
  - `display_name`
  - `sync_mode`
  - `sync_interval_minutes`
  - `visibility_scope`
  - `selection_mode`
  - `provider_metadata`
- Important error states:
  - unauthorized caller
  - duplicate or invalid resource selection
  - invalid visibility or sync policy
- Example request:

```json
{
  "resource_kind": "repository_evidence",
  "external_id": "org/repo",
  "display_name": "Operations repository evidence",
  "sync_mode": "auto",
  "sync_interval_minutes": 60,
  "visibility_scope": "evidence_only",
  "selection_mode": "browse"
}
```

### `POST /v1/connectors/{connection_id}/resources/upload`

- Purpose: create a resource from an uploaded snapshot, currently used for Notion export uploads.
- Caller:
  - workspace scope: `owner` or `admin`
  - personal scope: owning user
- Request body: multipart upload with source metadata plus the uploaded file.
- Response model: `ConnectorResourceSummary`
- Important behavior:
  - uploaded Notion exports are stored as `selection_mode = export_upload`
  - upload-backed resources default to `visibility_scope = evidence_only`
  - upload-backed resources are not live re-syncable

### `PATCH /v1/connectors/{connection_id}/resources/{resource_id}`

- Purpose: update resource metadata such as label, visibility, or sync policy.
- Caller: same access rules as resource creation.
- Request model: `ConnectorResourceUpdateRequest`

### `DELETE /v1/connectors/{connection_id}/resources/{resource_id}`

- Purpose: remove a managed resource.
- Caller: same access rules as resource creation.

### `POST /v1/connectors/{connection_id}/resources/{resource_id}/sync`

- Purpose: trigger an immediate live sync for a resource.
- Caller: same access rules as resource creation.
- Response shape: sync job enqueue/result payload.
- Important error states:
  - upload-backed snapshot resources reject manual sync
  - unauthorized caller
  - missing or inactive resource

### `GET /v1/connectors/{connection_id}/items`

- Purpose: inspect synced items associated with a resource.
- Caller: same access rules as connection detail.
- Response model: synced item list shape defined in `connectors.py`

## Provider-specific contract notes

- Google Drive:
  - workspace templates are shared drives and folders
  - default visibility is `member_visible`
- GitHub:
  - `repository_docs` syncs repository docs into member-visible knowledge by default
  - `repository_evidence` syncs text-based repository evidence into glossary support by default
- Notion:
  - `page` and `database` are live connector resources
  - `export_upload` is a snapshot upload resource and is not sync-now capable
