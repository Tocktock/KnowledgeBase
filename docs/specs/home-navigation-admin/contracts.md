# Home, Navigation, and Admin Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/workspace.py`
- `internal_kb_fullstack/backend/app/schemas/auth.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend page

### `GET /`

- Purpose: role-aware product front door.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - uses workspace overview data to render anonymous, member, or admin variants

## Backend home data API

### `GET /v1/workspace/overview`

- Purpose: deliver the aggregate home-page contract.
- Caller: anonymous or authenticated user.
- Response model: `WorkspaceOverviewResponse`
- Important fields:
  - `authenticated`
  - `workspace`
  - `viewer_role`
  - `can_manage_connectors`
  - `setup_state`
  - `next_actions`
  - `source_health`
  - `featured_docs`
  - `featured_concepts`
  - `recent_sync_issues`
  - `latest_validation_run`
  - `review_required_count`
- Important behavior:
  - anonymous viewers receive unauthenticated marketing-style data only
  - signed-in users without a current workspace receive `authenticated=true`, `workspace=null`, and a dedicated setup state rather than the anonymous view
  - members receive the consumer-oriented view
  - admins receive the consumer-oriented view plus operational summaries

## Shared layout contract

- The shared app shell always exposes a visible auth entry.
- Authenticated users see an account surface instead of a login button.
- Manage navigation items are shown only to authorized workspace admins.
