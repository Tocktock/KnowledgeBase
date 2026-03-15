# 0001 - Canonical write boundary

## Status
Accepted

## Decision
Canonical knowledge data is written only through backend application services.

The main write services are:
- `app.services.ingest`
- `app.services.jobs`
- worker-side indexing flows in `app.services.worker`

HTTP routes are orchestration adapters. They should not own transaction commits for canonical writes.

## Why
Mixed transaction ownership made the system harder to reason about. Some routes committed directly while other writes committed inside services.

That created ambiguity about where the unit of work starts and ends.

## Consequences
- Write services own `commit()`.
- Read services stay side-effect free.
- Routes should validate input, call a service, and map the result to a response.
