---
date: 2026-04-01
feature: repository-review
type: rationale
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
  - /docs/decisions/project-memory.md
status: active
---

# Rationale note: ontology and corpus review

## Context

This note records the ontology-focused portion of the 2026-04-01 repository-wide review. It treats the current working tree as authoritative and includes the local `sample-data/` corpus as on-disk context rather than tracked source.

Corpus baseline:

- `sample-data/` is ignored by root `.gitignore:14`
- local corpus size at review time: `13,893` files / `71M`
- current importer: `internal_kb_fullstack/backend/scripts/import_sample_corpus.py`

## Business ontology

### Actors

- `anonymous user`: can browse public read surfaces that resolve through the default workspace
- `authenticated user`: has a session and may or may not have a current workspace
- `workspace member`: the primary actor for reading, requesting concepts, and authoring in the current UI
- `workspace admin or owner`: the operational actor for connector setup, jobs, validation review, and direct evidence-only reads

### Workspace

- `workspace` is the primary tenancy boundary for documents, connectors, concepts, jobs, and memberships
- `current_workspace` is part of session context rather than a global singleton

### Source and resource

- `source` is the human-level notion of where knowledge came from
- `connection` and `resource` are the operational connector entities that realize that source inside the product

### Document and evidence

- `document` is the public knowledge object
- `evidence` is a supporting artifact that may remain `member_visible` or `evidence_only`
- the product intentionally distinguishes consumable knowledge from operational evidence

### Concept and review

- `concept` is a curated semantic object with lifecycle and verification state
- `review` spans concept requests, validation runs, verification policy, and approval workflows

### Job

- `job` is the operator-facing representation of background work such as embedding, connector sync, glossary refresh, and validation

## Formal ontology

### Persisted entities and identifiers

- workspace identity persists through `workspaces`, `workspace_memberships`, `workspace_invitations`, and `user_sessions.current_workspace_id`
- connector identity persists through `connector_oauth_states`, `connector_connections`, and `connector_resources`
- document identity persists through `documents`, `document_revisions`, `document_chunks`, and `document_links`
- concept identity persists through `knowledge_concepts`, `concept_support`, `glossary_jobs`, `glossary_validation_runs`, and verification-policy fields

### Invariants and uniqueness

- document revision and chunk invariants are codified in `project-memory.md:5-10`
- document slug identity is now workspace-scoped in the model layer instead of globally unique
- concept public identity is now persisted as workspace-scoped `public_slug`

### Visibility rules

- `documents.visibility_scope` is the formal evidence boundary
- member-facing list/search/detail reads default to `member_visible`
- current-workspace admins and owners may opt into direct `evidence_only` reads on detail surfaces

### State machines and transitions

- documents: `draft | published | archived`
- connector and job execution: queued, processing, failed, completed variants across job tables
- concepts: editorial lifecycle and separate verification lifecycle
- sessions: authenticated user plus mutable current-workspace transition

## Surface ontology

The frontend and public contracts currently make users believe the world contains:

- one canonical docs surface at `/docs/[slug]`
- one canonical concept surface at `/glossary/[slug]`
- one operator job surface at `/jobs`
- one set of authoring pages at `/new`, `/new/manual`, `/new/upload`, `/new/definition`
- one shared trust vocabulary across search, docs, concepts, and home

This surfaced ontology is mostly coherent, but it currently carries four user-visible ambiguities:

- authoring behaves as a workspace-member-only action even though the spec still says authenticated user
- reindex exists in the backend contract but not in the frontend surface
- `source_url` looks like a guaranteed link even when it can be a locator
- Sync Status claims connector-job inspectability but the backend connector-job branch is not executable

## Corpus ontology

The local sample corpus reinforces the product model in one important way: it is heavily evidence-shaped rather than polished-document-shaped. Meetings, CSV exports, operational notes, and nested Markdown pages all justify the product’s distinction between `member_visible` knowledge and `evidence_only` support.

The same corpus also distorts ontology in two ways:

- provenance is flattened because import writes `source_url=file.relative_path` and defaults `source_system` to a broad export label
- owner attribution is heuristic because `infer_owner_team()` derives ownership from path substrings rather than authoritative source metadata

The corpus therefore validates the need for evidence and verification, but it should not be mistaken for a perfect provenance fixture.

## Drift matrix

| business term | persisted representation | surfaced representation | mismatch or ambiguity | severity | affected specs and code |
| --- | --- | --- | --- | --- | --- |
| `sync status job inspection` | `embedding_jobs`, `glossary_jobs`, `connector_sync_jobs`; connector jobs need `ConnectorConnection` for workspace scoping | `/jobs` admin page and `/v1/jobs` contract imply recent job history across job families | connector-job branch raises `NameError` at runtime because `ConnectorConnection` is referenced but not imported | `P1` | `docs/specs/sync-status/spec.md:22-49`; `internal_kb_fullstack/backend/app/services/jobs.py:11-12,140-150,244-252`; `internal_kb_fullstack/backend/app/api/routes/admin.py:17-38` |
| `document author` | backend authoring routes require authenticated user and workspace context for writes | `/new*` pages are workspace-member guarded | spec still says `authenticated user`, so the actor in the docs is broader than the actor in the UI | `P2` | `docs/specs/document-authoring/spec.md:56-60`; `docs/specs/document-authoring/contracts.md:10-32`; `internal_kb_fullstack/frontend/app/new/*.tsx`; `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:130-173` |
| `document maintenance` | backend reindex route exists, but `request_document_reindex()` uses member-visible read lookup | no frontend reindex affordance | write-authorized maintenance is both under-surfaced and too tightly coupled to read visibility | `P2` | `docs/specs/document-authoring/spec.md:53-67`; `docs/specs/document-authoring/contracts.md:91-97`; `internal_kb_fullstack/backend/app/services/jobs.py:63-82`; `internal_kb_fullstack/frontend/components/editor/document-editor.tsx:60-694` |
| `source provenance` | `source_system`, `source_external_id`, `source_url` on documents | docs, trust badges, and specs present `source_url` as if it were the original source location | one field currently serves both canonical URLs and generic locators, so provenance looks stronger than it is | `P2` | `docs/specs/system-overview/spec.md:70-81`; `docs/specs/search-and-docs/spec.md:38-69`; `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:182-199`; `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx:57-63` |
| `owner team` | `documents.owner_team` | owner labels appear in docs and concepts surfaces | sample corpus import infers ownership heuristically from file paths rather than authoritative source metadata | `P3` | `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:95-112`; `internal_kb_fullstack/backend/app/db/models.py`; frontend owner-team labels across docs and concepts |
| `workspace-first connector model` | live tables and routes already depend on workspaces and workspace-owned connectors | feature specs treat workspace-first connectors as current behavior | durable decision layer still says this model is proposed or pending | `P2` | `docs/specs/connectors/spec.md:22-43`; `docs/decisions/0005-workspace-data-connectors.md:3-5`; `docs/decisions/project-memory.md:19-31`; `internal_kb_fullstack/backend/app/db/models.py:233-345` |

## Conclusion

The repository ontology is directionally coherent: workspace is the primary boundary, documents are public knowledge objects, concepts are curated semantic objects, evidence remains distinct from browsing, and jobs are an operator-facing support layer. The remaining drifts are concentrated where user-facing terminology or maintenance flows no longer cleanly match the formal model.
