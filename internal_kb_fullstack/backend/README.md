# Internal KB Backend

Backend-first internal knowledge base built for Docker Compose, PostgreSQL, pgvector, and remote embeddings.

## What this app does

- Stores canonical internal documents in PostgreSQL.
- Keeps immutable document revisions.
- Chunks documents into retrieval-ready sections.
- Generates embeddings remotely through the OpenAI-compatible embeddings API.
- Caches embeddings by content hash to avoid repeated remote calls.
- Uses PostgreSQL full-text search + pgvector semantic search with hybrid ranking.
- Runs embedding work asynchronously through a Postgres-backed job queue.

## Why this shape

This backend is optimized for internal docs rather than generic CMS records:

- `documents` stores the durable identity and ownership metadata.
- `document_revisions` stores immutable source snapshots.
- `document_chunks` stores retrieval units, not just raw documents.
- `embedding_cache` deduplicates repeated sections across revisions and sources.
- `embedding_jobs` keeps the worker and API loosely coupled without Redis.
- `document_links` stores the internal link graph as a projection.

## Stack

- FastAPI API server
- SQLAlchemy + psycopg 3
- PostgreSQL 17 + pgvector
- tiktoken for token-aware chunking
- OpenAI Python SDK for remote embeddings
- Docker Compose for local/ops deployment

## Quick start

1. Copy `.env.example` to `.env`.
2. Set `EMBEDDING_API_KEY`.
3. Start the stack:

```bash
docker compose up --build
```

API docs:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Important configuration

```env
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
CHUNK_TARGET_TOKENS=600
CHUNK_MAX_TOKENS=800
CHUNK_OVERLAP_TOKENS=80
EMBEDDING_BATCH_SIZE=32
EMBEDDING_REQUEST_MAX_TOTAL_TOKENS=6000
```

## Design notes

### 1. Embedding optimization

The worker optimizes remote embedding cost and latency through:

- chunk content hashing
- embedding cache reuse
- multi-input batching per API call
- token-budget-aware batching
- background processing through DB jobs

### 2. Search strategy

Search is hybrid:

- keyword: PostgreSQL `tsvector` + `ts_rank_cd`
- semantic: pgvector cosine distance
- fusion: reciprocal rank fusion (RRF)

### 3. Database ownership

Only the backend writes canonical data. If you connect another UI later, keep it read-only or route writes through the API.

## Example ingestion

```bash
curl -X POST http://localhost:8000/v1/documents/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "source_system": "manual",
    "title": "인프라 배포 가이드",
    "content_type": "markdown",
    "content": "# 배포\n\n이 문서는 배포 절차를 설명합니다.\n\n## 점검\n\n배포 전 체크리스트를 확인합니다.",
    "doc_type": "runbook",
    "language_code": "ko",
    "owner_team": "platform"
  }'
```

## Example search

```bash
curl -X POST http://localhost:8000/v1/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "배포 전 체크리스트",
    "limit": 5
  }'
```

## Main endpoints

- `GET /healthz`
- `GET /readyz`
- `POST /v1/documents/ingest`
- `POST /v1/documents/upload`
- `GET /v1/documents/{document_id}`
- `POST /v1/documents/{document_id}/reindex`
- `POST /v1/search`
- `GET /v1/jobs`

## Schema caveat

`EMBEDDING_DIMENSIONS` is baked into the initial schema migration. If you change it after first boot, rebuild the database volume or add a migration that recreates vector columns and indexes.

## Suggested next steps

- Add Notion adapter ingestion.
- Add repo fact ingestion.
- Add batch backfill mode for very large corpora.
- Add auth/SSO and tenant isolation.


## Decision records

See `../docs/decisions/` for durable architecture decisions and project memory.
