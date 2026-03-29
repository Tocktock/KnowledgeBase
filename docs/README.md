# KnowledgeHub Documentation

This folder is the canonical documentation home for the repository.

## Documentation model

- [`specs/`](./specs/): canonical feature behavior and product requirements
- [`decisions/`](./decisions/): architectural decisions and durable technical rules
- [`memories/`](./memories/): conversations, intentions, deprecations, and rationale history

## Source of Truth rules

- Feature behavior must be documented in `docs/specs/`.
- Architectural choices and long-lived invariants belong in `docs/decisions/`.
- Traceability and rationale belong in `docs/memories/`.
- Files outside `docs/` may summarize and link, but they must not restate detailed feature behavior as a second Source of Truth.

## Current feature specs

- [`system-overview`](./specs/system-overview/spec.md)
- [`workspace-auth`](./specs/workspace-auth/spec.md)
- [`home-navigation-admin`](./specs/home-navigation-admin/spec.md)
- [`connectors`](./specs/connectors/spec.md)
- [`search-and-docs`](./specs/search-and-docs/spec.md)
- [`document-authoring`](./specs/document-authoring/spec.md)
- [`concepts`](./specs/concepts/spec.md)
- [`glossary-validation`](./specs/glossary-validation/spec.md)
- [`sync-status`](./specs/sync-status/spec.md)
- [`public surface coverage matrix`](./specs/public-surface-coverage.md)

## Existing architecture records

- [`decisions/README.md`](./decisions/README.md)
- [`project-memory.md`](./decisions/project-memory.md)

## Required maintenance workflow

1. Update the relevant feature spec before or during implementation.
2. Record the intent, rationale, or deprecation note in `docs/memories/` when behavior or direction changes.
3. Keep high-level READMEs short and link back here instead of duplicating feature detail.
4. Document the current working tree behavior and public contracts, not a stale or previously released baseline.
