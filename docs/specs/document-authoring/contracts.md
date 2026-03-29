# Document Authoring Contracts

Canonical schema modules:

- `internal_kb_fullstack/backend/app/schemas/documents.py`
- `internal_kb_fullstack/backend/app/schemas/trust.py`

## Frontend page

### `GET /new`

- Purpose: mode chooser for manual authoring, upload-first authoring, and definition-draft authoring.
- Caller: authenticated user.
- Response: HTML page rendered by the frontend app.

### `GET /new/manual`

- Purpose: dedicated manual document authoring page.
- Caller: authenticated user.
- Response: HTML page rendered by the frontend app.

### `GET /new/upload`

- Purpose: dedicated upload-first authoring page.
- Caller: authenticated user.
- Response: HTML page rendered by the frontend app.

### `GET /new/definition`

- Purpose: dedicated definition-draft authoring page.
- Caller: authenticated user.
- Response: HTML page rendered by the frontend app.

## Backend write APIs

### `POST /v1/documents/ingest`

- Purpose: create or update a canonical document revision from manual authoring input.
- Caller: authenticated user.
- Request model: `IngestDocumentRequest`
- Important request fields:
  - `source_system`
  - `title`
  - `slug`
  - `content`
  - `content_type`
  - `doc_type`
  - `owner_team`
  - `visibility_scope`
  - `allow_slug_update`
  - `metadata`
- Response model: write-side document result from `documents.py`
- Important error states:
  - slug conflict when `allow_slug_update` is false
  - invalid document payload
  - unauthorized caller
- Example request:

```json
{
  "source_system": "manual",
  "title": "Validation glossary operator guide",
  "slug": "validation-glossary-operator-guide",
  "content_type": "markdown",
  "content": "# Validation glossary operator guide\n\nThis page explains how QA operators review changed terms.",
  "doc_type": "guide",
  "visibility_scope": "member_visible"
}
```

### `POST /v1/documents/upload`

- Purpose: upload a file and create an authoring draft from it.
- Caller: authenticated user.
- Request body: multipart file upload plus document metadata.
- Response model: upload result defined in `documents.py`
- Important error states:
  - unsupported file type
  - extraction failure
  - unauthorized caller

### `POST /v1/documents/generate-definition`

- Purpose: generate a draft glossary definition from support evidence.
- Caller: authenticated user.
- Request model: `GenerateDefinitionDraftRequest`
- Response model: generated draft shape defined in `documents.py`
- Important behavior:
  - the response is a draft seed, not an auto-approved glossary change

### `POST /v1/documents/{document_id}/reindex`

- Purpose: re-run indexing and chunk refresh for a document after content changes.
- Caller: authenticated user with write access to the document path.
- Response shape: reindex enqueue/result payload.
- Important error states:
  - unknown document
  - unauthorized caller
