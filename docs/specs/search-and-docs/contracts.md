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
  - result ranking, concept grounding, and canonical glossary promotion are all scoped to the resolved workspace
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
  - listing is scoped to the resolved workspace

### `GET /v1/documents/slug/{slug}`

- Purpose: resolve a document by slug.
- Caller: anonymous or authenticated user.
- Response model: `DocumentViewResponse`
- Important behavior:
  - anonymous viewers and non-admin members receive only `member_visible` documents
  - current-workspace owners and admins may resolve `evidence_only` documents directly
- Important error states:
  - unknown slug
  - filtered or inaccessible document
  - slug exists in another workspace only

### `GET /v1/documents/{document_id}`

- Purpose: resolve a document by document id.
- Caller: anonymous or authenticated user.
- Response model: `DocumentViewResponse`
- Important behavior:
  - the same evidence-only visibility rule applies as slug-based detail

### `GET /v1/documents/{document_id}/content`

- Purpose: fetch the rendered or source content for a document.
- Caller: anonymous or authenticated user.
- Response model: `DocumentContentResponse`
- Important behavior:
  - the same evidence-only visibility rule applies as document detail

### `GET /v1/documents/{document_id}/relations`

- Purpose: fetch outgoing links, backlinks, and related concepts for a document.
- Caller: anonymous or authenticated user.
- Response model: `DocumentRelationsResponse`
- Important behavior:
  - outgoing links, backlinks, and related documents are scoped to the same resolved workspace as the document detail page
  - the same evidence-only visibility rule applies as document detail

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
