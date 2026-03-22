# KnowledgeHub

KnowledgeHub is a full-stack internal knowledge base project built around a clear split:

- a FastAPI backend that owns canonical document data, chunking, indexing, and embedding jobs
- a Next.js frontend that provides the authoring, browsing, and search experience
- a PostgreSQL + pgvector database that stores both the system of record and the search index

This repository is organized so that the actual application lives under `internal_kb_fullstack/`, while the repository root provides top-level onboarding and a one-shot startup script.

For a full product-level explanation of the shipped glossary-aware system, read [`PRODUCT.md`](./PRODUCT.md).

## What This Repository Contains

At the root level:

- `README.md`: this document
- `PRODUCT.md`: comprehensive product documentation
- `one-shot.sh`: a one-command launcher for the full stack
- `internal_kb_fullstack/`: the actual application source code and Compose stack

Inside `internal_kb_fullstack/`:

- `frontend/`: Next.js 16 app
- `backend/`: FastAPI app, worker, schema installer, tests
- `docker-compose.yml`: full local runtime
- `docs/decisions/`: architecture decisions and project memory
- `Makefile`: convenience commands for common dev tasks

## Product Summary

The product is an internal wiki / knowledge base with two design influences:

- Notion-style writing experience:
  - focused authoring
  - visual editing
  - document metadata
- Wiki-style navigation:
  - slug-based URLs
  - internal links
  - backlinks
  - related documents
  - semantic search

The current implementation supports:

- document ingestion from structured payloads
- file upload ingestion
- immutable document revisions
- token-aware chunking
- internal link extraction
- async embedding job processing
- hybrid search using PostgreSQL full-text search plus pgvector
- a Next.js UI for dashboard, search, docs, new document creation, and jobs

## High-Level Architecture

The runtime is composed of five services:

1. `postgres`
   - source of truth for documents, revisions, chunks, jobs, and links
   - also used as the lightweight job queue
2. `migrate`
   - one-shot schema installer / migrator
3. `api`
   - FastAPI service for ingestion, retrieval, search, and admin-style job endpoints
4. `worker`
   - background processor that claims embedding jobs and writes vectors
5. `web`
   - Next.js frontend served through Node

### Request and Data Flow

The main ingest path is:

1. A client sends a document to `POST /v1/documents/ingest` or uploads a file.
2. The API normalizes the document and writes a new immutable revision.
3. The API chunks the content into retrieval-ready units.
4. The API updates the document link projection.
5. The API enqueues an embedding job in PostgreSQL.
6. The worker claims the job with a database-backed queue pattern.
7. The worker reuses cached embeddings when possible.
8. Missing vectors are requested from the remote embedding provider.
9. Chunks become searchable through both keyword and vector ranking.

The main search path is:

1. A user submits a search query.
2. The backend embeds the query.
3. PostgreSQL returns keyword candidates and vector candidates.
4. The backend fuses them with reciprocal rank fusion.
5. The frontend renders the ranked document hits.

## Repository Map

### Root

- `README.md`
- `one-shot.sh`
- `.gitignore`

### Application Root

`internal_kb_fullstack/`

- `.env.example`
- `.gitignore`
- `Makefile`
- `README.md`
- `docker-compose.yml`
- `docs/decisions/`
- `backend/`
- `frontend/`

### Backend

`internal_kb_fullstack/backend/`

- `app/main.py`: FastAPI application entrypoint
- `app/worker_main.py`: worker entrypoint
- `app/api/routes/`: route modules
- `app/db/`: engine, models, SQL schema files
- `app/services/`: ingestion, chunking, embeddings, jobs, search, wiki graph
- `app/schemas/`: request / response models
- `tests/`: backend tests
- `docs/architecture.md`: focused backend architecture summary
- `pyproject.toml`: Python dependencies and pytest config

### Frontend

`internal_kb_fullstack/frontend/`

- `app/`: Next.js app router pages and route handlers
- `components/`: UI and feature components
- `lib/`: API helpers, shared types, utilities
- `store/`: client-side UI state
- `package.json`: Node dependencies and scripts

## Key Functional Areas

### 1. Document Storage Model

The backend is not a generic CMS. It is optimized for internal knowledge retrieval. The important data concepts are:

- `documents`
  - stable identity
  - ownership metadata
  - source keys
  - current revision pointer
- `document_revisions`
  - immutable source snapshots
- `document_chunks`
  - retrieval-sized text units
  - full-text and vector indexed
- `embedding_cache`
  - de-duplicates embeddings by content hash and model configuration
- `embedding_jobs`
  - database-backed async work queue
- `document_links`
  - projected internal wiki-link graph for backlinks and related navigation

### 2. Search Strategy

Search is hybrid:

- keyword ranking from PostgreSQL full-text search
- semantic ranking from pgvector similarity
- fusion in SQL using reciprocal rank fusion

This gives better behavior than using only keyword matching or only vector search.

### 3. Frontend Delivery Model

The browser does not call the FastAPI service directly. Instead:

- the browser calls Next.js route handlers under `frontend/app/api/...`
- those handlers proxy requests to the backend service

This keeps the local Docker setup simple and avoids frontend-to-backend CORS friction.

## Main User-Facing Pages

The frontend currently exposes:

- `/`
  - dashboard and recent documents
- `/search`
  - semantic search UI
- `/docs`
  - document explorer
- `/docs/[slug]`
  - document detail page
  - content, headings, backlinks, related docs
- `/new`
  - new document authoring / upload
- `/jobs`
  - embedding job status view

## Main API Endpoints

Important backend endpoints include:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/documents`
- `GET /v1/documents/slug/{slug}`
- `GET /v1/documents/{document_id}`
- `GET /v1/documents/{document_id}/content`
- `GET /v1/documents/{document_id}/relations`
- `POST /v1/documents/ingest`
- `POST /v1/documents/upload`
- `POST /v1/documents/{document_id}/reindex`
- `POST /v1/search`
- `GET /v1/jobs`

## Quick Start

The easiest way to start the whole project from the repository root is:

```sh
./one-shot.sh
```

What the script does:

- checks that Docker and Docker Compose are available
- finds `internal_kb_fullstack/`
- creates missing `.env` files from `.env.example`
- chooses a free host port for Postgres on first setup
- runs `docker compose up -d --build`
- waits until:
  - `http://localhost:8000/healthz`
  - `http://localhost:8000/readyz`
  - `http://localhost:3000`
  are all reachable

When startup succeeds, the expected entrypoints are:

- web UI: `http://localhost:3000`
- backend docs: `http://localhost:8000/docs`
- backend OpenAPI JSON: `http://localhost:8000/openapi.json`

To stop the stack:

```sh
cd internal_kb_fullstack
docker compose down
```

## Manual Start

If you want to run the app manually instead of through the root launcher:

```sh
cd internal_kb_fullstack
cp .env.example .env
cp backend/.env.example backend/.env
docker compose up -d --build
```

Notes:

- `EMBEDDING_API_KEY` must be filled if you want actual embedding generation to work.
- The committed examples default to Postgres port `5432`, but your local `.env` can override this with `POSTGRES_PORT`.

## Local Development Commands

From `internal_kb_fullstack/`:

```sh
make up
make down
make logs
make migrate
make backend-compile
make backend-test
make openapi-export
```

Frontend commands from `internal_kb_fullstack/frontend/`:

```sh
npm install
npm run typecheck
npm run build
```

Backend commands from `internal_kb_fullstack/backend/`:

```sh
uv venv --python python3.12 .venv
. .venv/bin/activate
uv pip install -e '.[dev]'
pytest -q
python -m compileall app tests
```

## Configuration

Important environment variables include:

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_PORT`
- `DATABASE_URL`
- `API_PORT`
- `WEB_PORT`
- `KB_BACKEND_URL`
- `EMBEDDING_API_KEY`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSIONS`
- `CHUNK_TARGET_TOKENS`
- `CHUNK_MAX_TOKENS`
- `CHUNK_OVERLAP_TOKENS`
- `EMBEDDING_BATCH_SIZE`
- `EMBEDDING_REQUEST_MAX_TOTAL_TOKENS`

Important behavior note:

- `EMBEDDING_DIMENSIONS` is effectively baked into the current schema initialization. If you change it after the database is already created, you should recreate the database volume or introduce a migration that rebuilds the affected vector columns and indexes.

## How to Read the Codebase

If you are new to the repository, the best reading order is:

1. this root `README.md`
2. `internal_kb_fullstack/README.md`
3. `internal_kb_fullstack/backend/docs/architecture.md`
4. `internal_kb_fullstack/docs/decisions/README.md`
5. the service entrypoints:
   - `internal_kb_fullstack/backend/app/main.py`
   - `internal_kb_fullstack/backend/app/worker_main.py`
   - `internal_kb_fullstack/frontend/app/page.tsx`

Then focus on the backend core services:

- `app/services/ingest.py`
- `app/services/chunking.py`
- `app/services/embeddings.py`
- `app/services/search.py`
- `app/services/wiki_graph.py`

And the frontend integration layer:

- `frontend/lib/api/server.ts`
- `frontend/lib/api/proxy.ts`
- `frontend/app/api/...`

## Current Verification Status

The project has already been verified locally with:

- frontend dependency install
- frontend typecheck
- frontend production build
- backend dependency install with Python 3.12
- backend tests
- backend compile check
- full Docker Compose startup
- runtime checks against:
  - `/healthz`
  - `/readyz`
  - `/v1/documents`
  - the frontend home page

## Known Operational Notes

- The repository root is the Git root, but the application code is nested under `internal_kb_fullstack/`.
- Root `.env` files are intentionally not committed.
- The root launcher respects existing local `.env` files and will not overwrite them.
- If port `5432` is already occupied on your machine, the root launcher chooses a free Postgres host port on first setup.

## Where to Go Next

If your goal is:

- understand the product:
  - start with the dashboard, docs pages, and search page
- understand the runtime:
  - inspect Compose, `main.py`, and `worker_main.py`
- understand search quality:
  - inspect `search.py`, `embeddings.py`, and the SQL schema
- extend ingestion:
  - start from `ingest.py` and `parser.py`
- extend the UI:
  - start from `frontend/app/` and `frontend/components/`

## Reference Documents

Useful repo-local references:

- `internal_kb_fullstack/README.md`
- `internal_kb_fullstack/backend/README.md`
- `internal_kb_fullstack/backend/docs/architecture.md`
- `internal_kb_fullstack/docs/decisions/README.md`
- `internal_kb_fullstack/docs/decisions/project-memory.md`
