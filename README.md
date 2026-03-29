# KnowledgeHub

KnowledgeHub is a workspace knowledge layer. The runnable application lives in `internal_kb_fullstack/`, while the repository root provides onboarding, governance, and canonical project documentation.

## Start here

- Documentation index: [`docs/README.md`](./docs/README.md)
- Feature specs: [`docs/specs/`](./docs/specs/)
- Architecture decisions: [`docs/decisions/`](./docs/decisions/)
- Traceability history: [`docs/memories/`](./docs/memories/)
- Application source: [`internal_kb_fullstack/`](./internal_kb_fullstack/)

`PRODUCT.md` is retained only as a compatibility pointer and is not a Source of Truth for feature behavior.

## Repository layout

- `AGENTS.md`: repository-level working rules
- `docs/`: canonical project documentation
- `one-shot.sh`: one-command launcher
- `internal_kb_fullstack/`: application code, runtime config, frontend, backend, and tests

## Quick start

```sh
cd internal_kb_fullstack
cp .env.example .env
docker compose up --build
```

Local endpoints:

- frontend: `http://localhost:3000`
- backend OpenAPI: `http://localhost:8000/docs`

## Runtime summary

The application uses:

- FastAPI for API and background job orchestration
- Next.js for the web app
- PostgreSQL + pgvector for canonical storage and search
- a worker process for asynchronous embedding and validation jobs

For runtime and feature behavior, use the canonical docs instead of this README.
