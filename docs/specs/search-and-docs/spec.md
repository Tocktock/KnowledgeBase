# Search and Docs

## Summary

The member-facing knowledge experience is built around trusted search and document browsing. Search and docs must surface provenance and freshness while keeping evidence-only corpus material out of normal member views. All read-side retrieval must stay inside a single resolved workspace boundary so one workspace never leaks another workspace’s documents or glossary concepts.

## Primary users

- workspace members looking for reliable answers
- workspace admins validating whether synced knowledge remains trustworthy

## Current surfaces and owned routes

- Frontend pages:
  - `/search`
  - `/docs`
  - `/docs/[slug]`
- Backend public routes:
  - read-side document APIs under `/v1/documents/*`
  - search APIs under `/v1/search*`

## Current behavior

- `/search` is the main retrieval surface.
- `/docs` and `/docs/[slug]` are the main document browsing surfaces.
- Member-facing search and document lists must filter to `member_visible` content by default.
- Evidence-only documents may support glossary validation internally, but they must not appear in normal docs lists or member-facing search result sets.
- Direct document read routes are role-sensitive:
  - anonymous users and non-admin members can read only `member_visible` documents
  - current-workspace owners and admins may directly open `evidence_only` documents through the existing document detail, content, and relation routes
- Search may resolve exact glossary concepts and surface canonical glossary pages ahead of generic evidence.
- Read-side workspace resolution is server-side:
  - authenticated viewers use their current workspace
  - anonymous viewers and signed-in users without a current workspace fall back to the default workspace for public read surfaces

## Trust metadata

Search results, document detail, and concept-linked evidence share a normalized trust model:

- `source_label`
- `source_url`
- `authority_kind`
- `last_synced_at`
- `freshness_state`
- `evidence_count`

## Key workflows

- Search:
  - the user submits a natural-language query
  - the UI requests search results and explain data
  - result cards default to decision-support presentation with trust badges
  - detailed ranking and grounding explanation stays secondary
- Docs exploration:
  - the user browses a filtered document list
  - list rows surface trust and freshness rather than raw connector internals
  - direct slug routes open the canonical document detail page
- Docs detail:
  - the page foregrounds provenance, freshness, and related concepts
  - when an original source URL exists, the user can navigate back to it
- No-results:
  - authenticated users can pivot to manual authoring through `/new`

## Document detail rules

- Document detail should foreground provenance, freshness, and related concepts.
- When a canonical source URL exists, the detail page should link back to the original location.
- Trust and provenance should be visible without requiring the user to inspect operational pages.
- When admins directly open an `evidence_only` document, outgoing links, backlinks, and related documents follow the same role-sensitive visibility mode for that request.

## Permissions and visibility

- Anonymous users can access the read-only retrieval surfaces.
- Member-visible filtering is the default on `/search`, `/docs`, and document detail navigation.
- Evidence-only documents may be used internally for glossary support and validation, but they are not listed in default member browsing experiences.
- Direct evidence-only document reads are reserved for current-workspace owners and admins; they are not a separate public route family.
- Search, docs list, docs detail, backlinks, related documents, and concept grounding must all filter to the same resolved workspace.

## Important contracts owned by this spec

- search request and search result contracts
- search explanation contract
- document list, detail, content, and relation contracts
- shared trust object used by search and document read surfaces

## Constraints and non-goals

- Ranking/debug evidence may exist, but default search presentation should remain decision-support oriented rather than a scoring console.
- Evidence-only support rows are available to glossary validation workflows, not to default member search.
- This spec owns read-side docs and search behavior, not manual ingest or glossary approval mutations.

## Supporting docs

- [`contracts.md`](./contracts.md)
