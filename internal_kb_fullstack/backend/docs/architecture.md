# Architecture

## Runtime components

- `postgres`: source of truth and job queue
- `api`: ingestion, retrieval, reindex control plane
- `worker`: async embedding processor
- `migrate`: one-shot schema installer

## Request flow

1. Client calls `POST /v1/documents/ingest`.
2. API normalizes content and creates a new immutable revision.
3. API chunks the revision and inserts retrieval chunks.
4. API refreshes the `document_links` projection for the new revision.
5. API enqueues an embedding job.
6. Worker claims a queued job using `FOR UPDATE SKIP LOCKED`.
7. Worker reuses cached embeddings where possible.
8. Worker sends only missing chunks to the remote embedding provider.
9. Worker stores embeddings in cache and document chunks.
10. Search calls embed the user query and run hybrid ranking in Postgres.

## Core tables

### documents
Stable identity, ownership, source keys, and current revision pointer.

### document_revisions
Immutable revision snapshots.

### document_chunks
Searchable retrieval units with `tsvector` and `vector` data.

### embedding_cache
Deduplicated embeddings keyed by `content_hash + model + dimensions`.

### embedding_jobs
Lightweight work queue stored in Postgres.

### document_links
Internal wiki-link projection used for outgoing links and backlinks.

## Search ranking

- Vector top-K from pgvector HNSW
- Keyword top-K from PostgreSQL FTS
- RRF merge in SQL

## Why Postgres queue instead of Redis first

- Fewer moving parts for the first working system
- Strong transaction boundary with ingest + job creation
- Easier local ops under Docker Compose
- Good enough until concurrency or throughput justify an external broker
