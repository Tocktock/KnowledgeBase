# Public Surface Coverage

This matrix defines the current working-tree coverage target for product behavior and public contracts.

## Frontend page coverage

| Surface | Primary spec | Supporting docs | Main frontend file | Main backend dependency |
| --- | --- | --- | --- | --- |
| `/` | [`home-navigation-admin`](./home-navigation-admin/spec.md) | [`contracts`](./home-navigation-admin/contracts.md), [`states`](./home-navigation-admin/states.md) | `internal_kb_fullstack/frontend/app/page.tsx` | `GET /v1/workspace/overview` |
| `/login` | [`workspace-auth`](./workspace-auth/spec.md) | [`contracts`](./workspace-auth/contracts.md), [`flows`](./workspace-auth/flows.md) | `internal_kb_fullstack/frontend/app/login/page.tsx` | `/v1/auth/*`, `/v1/workspace/invitations/{token}/preview` |
| `/invite/[token]` | [`workspace-auth`](./workspace-auth/spec.md) | [`contracts`](./workspace-auth/contracts.md), [`flows`](./workspace-auth/flows.md) | `internal_kb_fullstack/frontend/app/invite/[token]/page.tsx` | `/v1/workspace/invitations/{token}/accept` |
| `/connectors` | [`connectors`](./connectors/spec.md) | [`contracts`](./connectors/contracts.md), [`flows`](./connectors/flows.md) | `internal_kb_fullstack/frontend/app/connectors/page.tsx` | `/v1/connectors/*` |
| `/connectors/setup/[provider]` | [`connectors`](./connectors/spec.md) | [`contracts`](./connectors/contracts.md), [`flows`](./connectors/flows.md) | `internal_kb_fullstack/frontend/app/connectors/setup/[provider]/page.tsx` | `/v1/connectors/*` |
| `/connectors/[connectionId]` | [`connectors`](./connectors/spec.md) | [`contracts`](./connectors/contracts.md), [`flows`](./connectors/flows.md) | `internal_kb_fullstack/frontend/app/connectors/[connectionId]/page.tsx` | `/v1/connectors/*` |
| `/search` | [`search-and-docs`](./search-and-docs/spec.md) | [`contracts`](./search-and-docs/contracts.md) | `internal_kb_fullstack/frontend/app/search/page.tsx` | `/v1/search`, `/v1/search/explain` |
| `/docs` | [`search-and-docs`](./search-and-docs/spec.md) | [`contracts`](./search-and-docs/contracts.md) | `internal_kb_fullstack/frontend/app/docs/page.tsx` | `/v1/documents` |
| `/docs/[slug]` | [`search-and-docs`](./search-and-docs/spec.md) | [`contracts`](./search-and-docs/contracts.md) | `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx` | `/v1/documents/slug/{slug}`, `/v1/documents/{id}/content`, `/v1/documents/{id}/relations` |
| `/new` | [`document-authoring`](./document-authoring/spec.md) | [`contracts`](./document-authoring/contracts.md), [`flows`](./document-authoring/flows.md) | `internal_kb_fullstack/frontend/app/new/page.tsx` | `/v1/documents/ingest`, `/v1/documents/upload`, `/v1/documents/generate-definition`, `/v1/documents/{id}/reindex` |
| `/new/manual` | [`document-authoring`](./document-authoring/spec.md) | [`contracts`](./document-authoring/contracts.md), [`flows`](./document-authoring/flows.md) | `internal_kb_fullstack/frontend/app/new/manual/page.tsx` | `/v1/documents/ingest` |
| `/new/upload` | [`document-authoring`](./document-authoring/spec.md) | [`contracts`](./document-authoring/contracts.md), [`flows`](./document-authoring/flows.md) | `internal_kb_fullstack/frontend/app/new/upload/page.tsx` | `/v1/documents/upload`, `/v1/documents/ingest` |
| `/new/definition` | [`document-authoring`](./document-authoring/spec.md) | [`contracts`](./document-authoring/contracts.md), [`flows`](./document-authoring/flows.md) | `internal_kb_fullstack/frontend/app/new/definition/page.tsx` | `/v1/documents/generate-definition`, `/v1/documents/ingest` |
| `/glossary` | [`concepts`](./concepts/spec.md) | [`contracts`](./concepts/contracts.md) | `internal_kb_fullstack/frontend/app/glossary/page.tsx` | `/v1/glossary` |
| `/glossary/requests` | [`concepts`](./concepts/spec.md) | [`contracts`](./concepts/contracts.md), [`glossary-validation/contracts`](./glossary-validation/contracts.md) | `internal_kb_fullstack/frontend/app/glossary/requests/page.tsx` | `/v1/glossary/requests` |
| `/glossary/[slug]` | [`concepts`](./concepts/spec.md) | [`contracts`](./concepts/contracts.md) | `internal_kb_fullstack/frontend/app/glossary/[slug]/page.tsx` | `/v1/glossary/slug/{slug}` |
| `/glossary/review` | [`glossary-validation`](./glossary-validation/spec.md) | [`contracts`](./glossary-validation/contracts.md), [`states`](./glossary-validation/states.md) | `internal_kb_fullstack/frontend/app/glossary/review/page.tsx` | `/v1/glossary/validation-runs`, `/v1/glossary/{concept_id}` mutations |
| `/glossary/review/[conceptId]` | [`glossary-validation`](./glossary-validation/spec.md) | [`contracts`](./glossary-validation/contracts.md), [`states`](./glossary-validation/states.md) | `internal_kb_fullstack/frontend/app/glossary/review/[conceptId]/page.tsx` | `/v1/glossary/{concept_id}`, `/v1/glossary/{concept_id}/draft`, `/v1/glossary/validation-runs` |
| `/jobs` | [`sync-status`](./sync-status/spec.md) | [`contracts`](./sync-status/contracts.md) | `internal_kb_fullstack/frontend/app/jobs/page.tsx` | `/v1/jobs`, `/v1/jobs/{job_id}` |

## Backend public route coverage

| Route module | Paths or endpoint family | Primary spec | Canonical schema modules |
| --- | --- | --- | --- |
| `auth.py` | `GET /v1/auth/google/start` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `GET /v1/auth/google/callback` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `POST /v1/auth/password/login` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `POST /v1/auth/password/invite-signup` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `POST /v1/auth/password/reset-links` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `GET /v1/auth/password/reset/{token}` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `POST /v1/auth/password/reset/{token}` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `auth.py` | `GET /v1/auth/me`, `POST /v1/auth/logout` | [`workspace-auth`](./workspace-auth/spec.md) | `auth.py` |
| `workspace.py` | `GET /v1/workspace`, `GET /v1/workspace/members` | [`workspace-auth`](./workspace-auth/spec.md) | `workspace.py` |
| `workspace.py` | `GET /v1/workspace/invitations/{token}/preview`, `GET /v1/workspace/invitations`, `POST /v1/workspace/invitations`, `POST /v1/workspace/invitations/{token}/accept` | [`workspace-auth`](./workspace-auth/spec.md) | `workspace.py` |
| `workspace.py` | `GET /v1/workspace/overview` | [`home-navigation-admin`](./home-navigation-admin/spec.md) | `workspace.py`, `trust.py`, `glossary.py` |
| `connectors.py` | `GET /v1/connectors/readiness`, `GET /v1/connectors`, `GET /v1/connectors/{connection_id}` | [`connectors`](./connectors/spec.md) | `connectors.py` |
| `connectors.py` | `POST /v1/connectors/{provider}/oauth/start`, `GET /v1/connectors/{provider}/oauth/callback` | [`connectors`](./connectors/spec.md) | `connectors.py` |
| `connectors.py` | `GET /v1/connectors/{connection_id}/browse` | [`connectors`](./connectors/spec.md) | `connectors.py` |
| `connectors.py` | `GET /v1/connectors/{connection_id}/resources`, `POST /v1/connectors/{connection_id}/resources`, `POST /v1/connectors/{connection_id}/resources/upload`, `PATCH /v1/connectors/{connection_id}/resources/{resource_id}`, `DELETE /v1/connectors/{connection_id}/resources/{resource_id}`, `POST /v1/connectors/{connection_id}/resources/{resource_id}/sync`, `GET /v1/connectors/{connection_id}/items` | [`connectors`](./connectors/spec.md) | `connectors.py`, `trust.py` |
| `documents.py` | `GET /v1/documents`, `GET /v1/documents/slug/{slug}`, `GET /v1/documents/{document_id}`, `GET /v1/documents/{document_id}/content`, `GET /v1/documents/{document_id}/relations` | [`search-and-docs`](./search-and-docs/spec.md) | `documents.py`, `trust.py` |
| `documents.py` | `POST /v1/documents/ingest`, `POST /v1/documents/upload`, `POST /v1/documents/generate-definition`, `POST /v1/documents/{document_id}/reindex` | [`document-authoring`](./document-authoring/spec.md) | `documents.py`, `trust.py` |
| `search.py` | `POST /v1/search`, `POST /v1/search/explain` | [`search-and-docs`](./search-and-docs/spec.md) | `search.py`, `trust.py` |
| `glossary.py` | `GET /v1/glossary`, `GET /v1/glossary/slug/{slug}`, `GET /v1/glossary/{concept_id}` | [`concepts`](./concepts/spec.md) | `glossary.py`, `trust.py` |
| `glossary.py` | `POST /v1/glossary/refresh`, `GET /v1/glossary/requests`, `POST /v1/glossary/requests`, `POST /v1/glossary/validation-runs`, `GET /v1/glossary/validation-runs`, `GET /v1/glossary/validation-runs/{run_id}`, `POST /v1/glossary/{concept_id}/draft`, `PATCH /v1/glossary/{concept_id}` | [`glossary-validation`](./glossary-validation/spec.md) | `glossary.py`, `jobs.py`, `trust.py` |
| `admin.py` | `GET /v1/jobs`, `GET /v1/jobs/{job_id}` | [`sync-status`](./sync-status/spec.md) | `jobs.py` |
| `health.py` | `GET /healthz`, `GET /readyz` | [`sync-status`](./sync-status/spec.md) | none; simple health payloads |

## Schema coverage checklist

Every current public schema module is referenced by at least one owning contract doc:

- `auth.py`: [`workspace-auth/contracts.md`](./workspace-auth/contracts.md)
- `workspace.py`: [`workspace-auth/contracts.md`](./workspace-auth/contracts.md), [`home-navigation-admin/contracts.md`](./home-navigation-admin/contracts.md)
- `connectors.py`: [`connectors/contracts.md`](./connectors/contracts.md)
- `documents.py`: [`search-and-docs/contracts.md`](./search-and-docs/contracts.md), [`document-authoring/contracts.md`](./document-authoring/contracts.md)
- `search.py`: [`search-and-docs/contracts.md`](./search-and-docs/contracts.md)
- `glossary.py`: [`concepts/contracts.md`](./concepts/contracts.md), [`glossary-validation/contracts.md`](./glossary-validation/contracts.md)
- `jobs.py`: [`glossary-validation/contracts.md`](./glossary-validation/contracts.md), [`sync-status/contracts.md`](./sync-status/contracts.md)
- `trust.py`: [`connectors/contracts.md`](./connectors/contracts.md), [`search-and-docs/contracts.md`](./search-and-docs/contracts.md), [`concepts/contracts.md`](./concepts/contracts.md), [`home-navigation-admin/contracts.md`](./home-navigation-admin/contracts.md)
