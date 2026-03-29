# Search and Docs Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/documents.py`
- `internal_kb_fullstack/backend/app/schemas/search.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend pages

### `GET /search`

- Purpose: primary member-facing retrieval surface.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.
- Important behavior:
  - issues search and explain requests for the submitted query
  - surfaces trust badges and a secondary explanation panel

### `GET /docs`

- Purpose: document exploration surface for member-visible knowledge.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.

### `GET /docs/[slug]`

- Purpose: canonical document detail surface for a document slug.
- Caller: anonymous or authenticated user.
- Response: HTML page rendered by the frontend app.

## Backend search APIs

### `POST /v1/search`

- Purpose: run the hybrid search pipeline over member-visible knowledge and concept grounding.
- Caller: anonymous or authenticated user.
- Request model: `SearchRequest`
- Important request fields:
  - `query`
  - `limit`
  - optional `doc_type`
  - optional `source_system`
  - optional `owner_team`
  - optional `include_debug_scores`
- Response model: `SearchResponse`
- Important behavior:
  - exact or high-confidence concept grounding may influence result framing
  - evidence-only documents are filtered from default result hits
- Example request:

```json
{
  "query": "How do glossary validation runs work?",
  "limit": 5
}
```

### `POST /v1/search/explain`

- Purpose: return the search explanation payload for the same query.
- Caller: anonymous or authenticated user.
- Request model: `SearchRequest`
- Response model: `SearchExplainResponse`

## Backend document read APIs

### `GET /v1/documents`

- Purpose: list member-visible documents for browsing.
- Caller: anonymous or authenticated user.
- Query parameters: list and filter parameters exposed by `documents.py`
- Response model: `DocumentListResponse`
- Important behavior:
  - default listing excludes `evidence_only` documents

### `GET /v1/documents/slug/{slug}`

- Purpose: resolve a document by slug.
- Caller: anonymous or authenticated user.
- Response model: `DocumentViewResponse`
- Important error states:
  - unknown slug
  - filtered or inaccessible document

### `GET /v1/documents/{document_id}`

- Purpose: resolve a document by document id.
- Caller: anonymous or authenticated user.
- Response model: `DocumentViewResponse`

### `GET /v1/documents/{document_id}/content`

- Purpose: fetch the rendered or source content for a document.
- Caller: anonymous or authenticated user.
- Response model: `DocumentContentResponse`

### `GET /v1/documents/{document_id}/relations`

- Purpose: fetch outgoing links, backlinks, and related concepts for a document.
- Caller: anonymous or authenticated user.
- Response model: `DocumentRelationsResponse`

## Shared trust contract

The following read-side payloads embed the normalized trust object from `trust.py`:

- `DocumentSummary`
- `DocumentViewResponse`
- `SearchHit`

Required trust fields:

- `source_label`
- `source_url`
- `authority_kind`
- `last_synced_at`
- `freshness_state`
- `evidence_count`
