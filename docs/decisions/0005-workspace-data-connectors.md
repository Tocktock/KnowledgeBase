# 0005 - Workspace data connectors are zero-config for end users

## Status
Accepted

## Decision
KnowledgeHub uses workspace-scoped connector ownership (`workspace | personal`) rather than deployment-scoped connector ownership (`shared | user`).

The durable connector model is:
- multi-tenant SaaS
- centrally managed OAuth applications
- invite-only workspace membership
- organization-admin-first setup
- sync-first ingestion into the existing document store

End users must not see or manage provider credentials, raw resource identifiers, or connector implementation fields.

Workspace admins connect data sources through a template-first flow:
- choose a provider template
- complete OAuth consent
- select the source with a provider-native picker or search UI
- confirm the default sync policy

Personal connectors remain available as a secondary feature, but workspace connectors are the primary product path.

## Why
The earlier deployment-scoped connector layer was structurally reusable, but it exposed too much of the internal model:
- provider/resource terminology
- raw resource kinds
- external identifiers
- low-level sync fields

That was acceptable for an admin console, but it was not acceptable for a zero-config product experience.

The product also needed a real workspace boundary so each customer organization could own membership, admin actions, and shared source setup independently. This decision records that workspace-first connector model as a durable architectural rule rather than a future migration target.

## Durable rules

### Workspace model
- `workspaces`, `workspace_memberships`, and `workspace_invitations` define the connector-management boundary.
- Membership roles are `owner | admin | member`.
- Workspace joins are invite-only.
- Sessions carry `current_workspace_id`.

### Connector ownership
- Shared organizational sources use `workspace` scope.
- Keep `personal` as a secondary scope for user-owned sources.
- Limit active connections to one row per `(workspace_id, scope, owner_user_id, provider)`.

### Provider abstraction
- Keep a provider catalog in code.
- Each provider declares capabilities such as:
  - auth mode
  - selection mode
  - supported templates
  - default sync policy
  - health state
  - share requirements
- Initial providers are `google_drive`, `github`, and `notion`.
- The model must be able to add future providers without changing the top-level UX structure.

### Source selection UX
- Default setup starts from provider templates and provider-native browse or search flows rather than raw resource CRUD.
- Advanced selection remains admin-only and collapsed by default.

### Document ingestion
- Connectors stay sync-first.
- Synced items flow into the existing document store and reuse the current `/docs`, search, and glossary pipelines.
- User-facing surfaces show only source labels such as `Google Drive`, `GitHub`, or `Notion`, not internal connector structure.
- Shared provenance uses the normalized `source_url` contract: `https://...`, `generic://<source_system>/<percent-encoded locator>`, or `null`.
- Only `https://...` is treated as an outbound original-source link. `generic://...` stays display-only provenance.

## Public interface direction
- Sessions expose `current_workspace_id`.
- Workspace membership APIs provide the current workspace, member list, and invite flow.
- Connector APIs default to workspace context and use `workspace | personal` scopes.
- Readiness responses remain provider-based, but they report workspace-specific setup state and recommended templates.
- Source creation stays provider-agnostic at the API layer, while the default UI always starts from a template instead of raw source CRUD.

## Consequences
- Connector APIs become workspace-aware.
- Admin UX becomes a setup wizard instead of a raw connector console.
- Regular members can consume synced content without ever opening connector management.
- Deployment-scoped connector ownership is no longer a valid architecture target for new work.

## Implementation defaults
- Workspace sources default to `auto` sync every 60 minutes.
- Personal sources default to `manual` sync.
- App login stays Google-based for now.
- Notion is a connector provider, not an app-login provider.
- Query-time chat connector UX is out of scope for this decision.
