# Sync Status Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/jobs.py`

## Frontend page

### `GET /jobs`

- Purpose: admin-facing sync and job-health page.
- Caller: authenticated `owner` or `admin`.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - non-admin viewers receive the manage-access guard

## Backend job APIs

### `GET /v1/jobs`

- Purpose: list background jobs and job summary counts.
- Caller: authenticated `owner` or `admin`.
- Response model: jobs list and summary shapes from `jobs.py`

### `GET /v1/jobs/{job_id}`

- Purpose: fetch one job detail record.
- Caller: authenticated `owner` or `admin`.
- Response model: job detail shape from `jobs.py`

## Backend health APIs

### `GET /healthz`

- Purpose: liveness check for the backend service.
- Caller: infrastructure or any HTTP client.
- Response shape: simple healthy status payload.

### `GET /readyz`

- Purpose: readiness check for the backend service and its dependencies.
- Caller: infrastructure or any HTTP client.
- Response shape: simple readiness payload.
- Important error states:
  - degraded dependency or startup readiness failure
