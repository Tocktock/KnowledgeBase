---
date: 2026-03-31
feature: repository-review
type: rationale
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/workspace-auth/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/home-navigation-admin/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0003-document-links-are-a-projection.md
  - /docs/decisions/0005-workspace-data-connectors.md
status: active
---

# Ontology and corpus review

## Context

This note records the ontology perspective requested for the repository-wide review:

- business/domain ontology: what the product claims the world contains
- formal ontology: what the code persists, how identity works, and how states transition

The note also captures how the repository-owned sample corpus reinforces or distorts that ontology.

## Ontology map

### Workspace, membership, and session

Primary evidence:

- `internal_kb_fullstack/backend/app/db/models.py:227-317`
- `internal_kb_fullstack/backend/app/services/workspace.py:62-99`
- `internal_kb_fullstack/backend/app/api/deps.py:20-46`
- `internal_kb_fullstack/frontend/components/auth/manage-access-guard.tsx:96-172`

Model:

- `workspace` is the top-level tenancy object
- `workspace_membership` binds a user to a workspace and role
- `user_session` binds an authenticated user to a current workspace context
- invitations and password-reset tokens are auxiliary identity-transition entities

Lifecycle and boundary observations:

- anonymous and authenticated users without membership both fall back to default-workspace read behavior on the backend
- the frontend distinguishes “not logged in” from “logged in but missing workspace membership”
- session identity is explicit, but workspace context is mutable per session

### Connector, provider, resource, and source item

Primary evidence:

- `internal_kb_fullstack/backend/app/db/models.py:116-168`
- `internal_kb_fullstack/backend/app/db/models.py:320-412`
- `internal_kb_fullstack/backend/app/services/connectors.py`

Model:

- `provider` is an enum-level capability family
- `connection` is an authenticated provider account bound to workspace ownership rules
- `resource` is the sync root selected from that connection
- `source_item` is the provider-native leaf that may project into a document

Lifecycle and boundary observations:

- ownership is modeled at the connection level through `workspace_id`, `owner_scope`, and optional `owner_user_id`
- visibility is modeled at the resource and then projected into documents
- sync jobs act on resources, not directly on documents

### Document, revision, chunk, and link

Primary evidence:

- `internal_kb_fullstack/backend/app/db/models.py:171-209`
- `internal_kb_fullstack/backend/app/db/models.py:415-470`
- `internal_kb_fullstack/backend/app/db/models.py:548-569`
- `internal_kb_fullstack/frontend/lib/types.ts:22-110`

Model:

- `document` is the public knowledge object
- `document_revision` is the immutable content snapshot
- `document_chunk` is the retrieval and embedding unit
- `document_link` is a projection from revision content to target slug and optional resolved target document

Lifecycle and boundary observations:

- the revision/chunk split is coherent and matches ADR `0002` and ADR `0003`
- the document public surface remains the main browse/read object
- visibility is attached to documents, not chunks, which is the correct business boundary

### Concept, request, support, validation, and verification

Primary evidence:

- `internal_kb_fullstack/backend/app/db/models.py:603-737`
- `internal_kb_fullstack/backend/app/services/glossary.py:336-528`
- `internal_kb_fullstack/backend/app/services/glossary.py:569-631`
- `internal_kb_fullstack/frontend/lib/types.ts:181-316`

Model:

- `knowledge_concept` is the curated domain object
- manual request intake is represented through concept-request and review flows in services and schemas
- `concept_support` binds documents or chunks as grounded evidence
- `glossary_validation_run` records validation execution state
- `glossary_verification_policy` records rules for durable approval

Lifecycle and boundary observations:

- concepts have two overlapping but distinct state machines:
  - editorial lifecycle: suggested, drafted, approved, stale, archived
  - verification lifecycle: verified, monitoring, drift_detected, evidence_insufficient, archived
- this is a strong design because it separates authoring from trustworthiness
- the main drift is public identity: the concept entity itself is persistent, but its public route key is derived from display text

### Job and worker

Primary evidence:

- `internal_kb_fullstack/backend/app/db/models.py:493-545`
- `internal_kb_fullstack/backend/app/db/models.py:683-737`
- `internal_kb_fullstack/backend/app/services/jobs.py:16-205`
- `internal_kb_fullstack/backend/app/api/routes/admin.py:14-38`
- `internal_kb_fullstack/frontend/app/jobs/page.tsx:1-18`

Model:

- jobs are persisted intents for embedding, connector sync, glossary generation, and validation runs
- workers are implicit runtime actors and not first-class persisted entities

Lifecycle and boundary observations:

- this matches the current product framing of Sync Status as a support surface
- it also means observability is job-centric rather than execution-centric

## Drift table

| Area | Spec ontology | Code ontology | Surfaced UI ontology | Net effect |
| --- | --- | --- | --- | --- |
| workspace read boundary | anonymous and member reads are workspace-scoped, with a clear no-membership state | backend resolves default workspace for anonymous and missing-membership reads | frontend distinguishes anonymous vs workspace-required | mostly aligned |
| evidence-only support | evidence-only exists to support validation without becoming ordinary docs | visibility_scope exists and is enforced on list/search but not all detail paths | support links are rendered like standard docs | partial enforcement weakens ontology |
| concept identity | concept behaves like a stable knowledge object | entity is stable, route identity is derived | UI fully trusts slug | identity instability leaks into UX |
| document identity | workspace is the primary storage boundary | migration is workspace-scoped, ORM still partially global | UI assumes workspace-relative doc routes | formal storage contract is inconsistent |
| job and worker | admin sees job health, not raw infrastructure | jobs exist, workers do not | UI shows job summaries only | acceptable now, limiting later |

## Corpus analysis

Primary evidence:

- `sample-data/sendy-knowledge/Product Home/회의록/제품팀 회의록 b77e9f4df30944dab670619fe9a12f67.md`
- `sample-data/sendy-knowledge/Product Home/회의록/제품팀 회의록/제품팀 회의록 9c77e01e97184e2bae39faa9e5cd299b_all.csv`
- `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:48-127`
- `internal_kb_fullstack/backend/scripts/import_sample_corpus.py:173-237`

Observations:

- the corpus is structurally a Notion-export-like knowledge dump with Markdown index pages, CSV tables, mixed Korean naming, and path-derived hierarchy
- Markdown often acts as a pointer page into CSV or nested content rather than a self-contained article
- the import script normalizes everything under one `source_system` default of `notion-export`
- CSV inputs become `doc_type="data"` and `content_type="text"`, while Markdown becomes `knowledge`
- ownership is inferred heuristically from path substrings such as `platform`, `ml`, `design`, `Product Home`, `ios`, and Korean squad names

What this reinforces:

- the glossary pipeline is grounded in operational evidence, meeting records, and exported team artifacts rather than only polished documents
- the domain model is therefore correctly shaped to distinguish member-visible knowledge from evidence-only support

What this distorts:

- provenance is flattened because `source_url` is set to a relative path and `source_system` defaults to one export label even when the source semantics vary
- team ownership becomes heuristic rather than authoritative metadata
- pointer-style Markdown and raw CSV tables can over-index concept extraction toward operational exhaust rather than curated definitions

## Impact

- The repository’s ontology is directionally coherent: workspace as boundary, documents as public knowledge, concepts as curated semantic objects, and jobs as operator support.
- The main breaks happen where persisted identity or visibility semantics are weakened at the public surface.
- The sample corpus validates the need for evidence-only pathways and verification policy, but it also shows why provenance and stable public identity need tighter modeling.

## Follow-up

- Any follow-up implementation should treat concept identity and evidence visibility as ontology-level repairs, not just bug fixes.
- If the corpus remains a long-term fixture, provenance metadata should become more expressive than `source_system + relative_path`.
