# Glossary Validation Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/glossary.py`
- `internal_kb_fullstack/backend/app/schemas/jobs.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend page

### `GET /glossary/review`

- Purpose: admin-only Knowledge QA surface.
- Caller: authenticated `owner` or `admin`.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - non-admin viewers receive the explicit manage-access guard instead of the full operational UI

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
