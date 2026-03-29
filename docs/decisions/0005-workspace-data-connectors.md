# 0005 - Workspace data connectors are zero-config for end users

## Status
Proposed

## Decision
The product moves from deployment-scoped connector ownership (`shared | user`) to workspace-scoped ownership (`workspace | personal`).

The default connector model is:
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

The first-class templates are:
- Google Drive shared drive
- Google Drive team folder
- Notion team wiki page
- Notion team database

Personal connectors remain available as a secondary feature, but workspace connectors are the primary product path.

## Why
The current connector layer is structurally reusable, but it still exposes too much of the internal model:
- provider/resource terminology
- raw resource kinds
- external identifiers
- low-level sync fields

That is acceptable for an admin console, but it is not acceptable for a zero-config product experience.

The product also currently assumes a single deployment-level admin model. That blocks the intended SaaS experience where each customer organization needs its own membership boundary, admin set, and shared data source catalog.

## Target architecture

### Workspace model
- Add `workspaces`, `workspace_memberships`, and `workspace_invitations`.
- Membership roles are `owner | admin | member`.
- Workspace joins are invite-only.
- Sessions carry `current_workspace_id`.

### Connector ownership
- Replace `shared` with `workspace`.
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
- Google Drive uses a native picker or a Drive-like browser. Manual identifier entry is not part of the default UI.
- GitHub uses repository search and a fixed `repository_docs` template that syncs README and `docs/` content only.
- Notion uses search plus recent items and must clearly warn that only pages or databases shared with the integration are visible.
- Advanced selection remains admin-only and collapsed by default.

### Document ingestion
- Connectors stay sync-first.
- Synced items flow into the existing document store and reuse the current `/docs`, search, and glossary pipelines.
- User-facing surfaces show only source labels such as `Google Drive`, `GitHub`, or `Notion`, not internal connector structure.

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
- Existing single-deployment connector data needs a migration path:
  - existing `shared` connections become default-workspace `workspace` connections
  - existing `user` connections become `personal` connections
  - existing admin emails seed the first workspace owners/admins

## Implementation defaults
- Workspace sources default to `auto` sync every 60 minutes.
- Personal sources default to `manual` sync.
- App login stays Google-based for now.
- Notion is a connector provider, not an app-login provider.
- Query-time chat connector UX is out of scope for this decision.

## Rollout shape
- First add workspace, membership, and invitation tables plus session context.
- Then migrate connector ownership from deployment-shared to workspace-first.
- Then replace the raw connector console with template-first admin setup and read-only member status views.
- After that, add more providers through the same capability catalog instead of building provider-specific top-level flows.
