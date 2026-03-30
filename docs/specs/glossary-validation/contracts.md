# Glossary Validation Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/glossary.py`
- `internal_kb_fullstack/backend/app/schemas/jobs.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend page

### `GET /glossary/review`

- Purpose: admin-only Knowledge QA overview and queue surface.
- Caller: authenticated `owner` or `admin`.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - non-admin viewers receive the explicit manage-access guard instead of the full operational UI

### `GET /glossary/review/[conceptId]`

- Purpose: admin-only dedicated concept review workspace.
- Caller: authenticated `owner` or `admin`.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - queue rows navigate here instead of expanding full detail inline on `/glossary/review`

## Backend glossary operational APIs

### `POST /v1/glossary/refresh`

- Purpose: refresh glossary support and suggestion state without starting a full validation run.
- Caller: authenticated `owner` or `admin`.
- Request model: glossary refresh request from `glossary.py`
- Response shape: refresh summary payload.

### `POST /v1/glossary/validation-runs`

- Purpose: create a workspace validation run.
- Caller: authenticated `owner` or `admin`.
- Request model: `GlossaryValidationRunCreateRequest`
- Allowed modes:
  - `sync_validate_impacted`
  - `sync_validate_full`
  - `validate_term`
- Optional request fields:
  - `target_concept_id`
  - `connector_resource_ids`
- Response model: `GlossaryValidationRunSummary`
- Important behavior:
  - when `connector_resource_ids` is omitted, the run targets active workspace resources
  - snapshot upload resources are counted as evidence but are skipped for live sync
- Example request:

```json
{
  "mode": "sync_validate_impacted"
}
```

### `POST /v1/glossary/requests`

- Purpose: create or update a user-requested glossary candidate for admin review.
- Caller: authenticated workspace member, admin, or owner with an active workspace membership.
- Request model: `GlossaryConceptRequestCreateRequest`
- Request fields:
  - `term`
  - `aliases`
  - `request_note`
  - `owner_team_hint`
- Response model: `GlossaryConceptRequestResponse`
- Response status meanings:
  - `created`: new suggested concept candidate was created
  - `updated_existing`: a matching non-approved candidate already existed and the new request was appended
  - `already_exists`: the term already exists as an approved concept
- Important behavior:
  - requests never auto-publish a concept
  - matching approved concepts are returned without opening a duplicate review item
  - matching suggested or drafted concepts keep one review item and accumulate request context in concept metadata
- Important error states:
  - no active workspace membership
  - invalid or empty term

### `GET /v1/glossary/requests`

- Purpose: list the current authenticated user's glossary requests in the current workspace.
- Caller: authenticated workspace member, admin, or owner with an active workspace membership.
- Query params:
  - `limit`
  - `offset`
- Response model: `GlossaryConceptRequestListResponse`
- Important behavior:
  - returns one item per requested concept candidate
  - each item includes the concept summary, the latest matching request metadata for the current user, and that user's request count for the concept
  - the route does not expose workspace-wide request intake
- Important error states:
  - no active workspace membership

### `GET /v1/glossary/validation-runs`

- Purpose: list recent validation runs.
- Caller: authenticated `owner` or `admin`.
- Response model: list of `GlossaryValidationRunSummary`

### `GET /v1/glossary/validation-runs/{run_id}`

- Purpose: fetch one validation run detail and summary.
- Caller: authenticated `owner` or `admin`.
- Response model: validation run detail shape defined in `glossary.py`

### `POST /v1/glossary/{concept_id}/draft`

- Purpose: create or refresh a working draft for a concept.
- Caller: authenticated `owner` or `admin`.
- Response shape: draft creation payload defined in `glossary.py`
- Important behavior:
  - when synced evidence exists, draft generation uses the support corpus
  - when the concept came from a manual request and no evidence exists yet, the system creates a fallback draft seeded from the request metadata so admins can continue the review path
  - for already-approved concepts whose evidence drifted, this route refreshes the working draft without unpublishing the current canonical page

### `PATCH /v1/glossary/{concept_id}`

- Purpose: perform glossary review actions on a concept.
- Caller: authenticated `owner` or `admin`.
- Request model: `GlossaryConceptUpdateRequest`
- Supported actions include:
  - `approve`
  - `ignore`
  - `mark_stale`
  - `suggest`
  - `merge`
  - `split`
- Important error states:
  - unknown concept
  - unsupported transition
  - invalid merge or split payload
  - verification policy unsatisfied
  - missing canonical glossary document
- Important behavior:
  - `approve` must fail unless the concept currently satisfies its assigned verification policy
  - verification-policy failures return a structured 4xx detail with a machine-readable code and missing requirements

## Shared operational shapes

- `GlossaryConceptSummary`
- `GlossaryValidationRunSummary`
- `GlossarySupportItem`

Important operational fields on concept summaries:

- `validation_state`
- `validation_reason`
- `last_validated_at`
- `review_required`
- `last_validation_run_id`
- `verification_state`
- `verification`

Verification summary fields:

- `status`
- `policy_label`
- `policy_version`
- `evidence_bundle_hash`
- `verified_at`
- `due_at`
- `last_checked_at`
- `verified_by`
- `reason`
