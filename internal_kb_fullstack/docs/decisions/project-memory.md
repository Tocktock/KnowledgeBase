# Project Memory

## Current invariants

- `documents.current_revision_id` must point to a revision that belongs to the same document.
- `document_chunks(document_id, revision_id)` must match an existing `(document_id, id)` pair in `document_revisions`.
- `embedding_jobs(document_id, revision_id)` must match an existing `(document_id, id)` pair in `document_revisions`.
- `document_links` is the source for outgoing links and backlinks.
- source-level checksum decides whether a new revision is created.
- canonical write paths commit inside application services, not inside HTTP routes.

## Operational notes

- This project assumes one active embedding dimension per deployment.
- If the embedding dimension changes, create a migration and rebuild vector indexes.
- If a future UI writes canonical data, route the write through backend services instead of writing tables directly.
- If link rules change, update both the ingestion projection logic and the frontend renderer rules.

## Pending follow-ups

- Replace handwritten frontend API types with generated types from backend OpenAPI.
- Split retrieval/search further if ranking policy grows more complex.
