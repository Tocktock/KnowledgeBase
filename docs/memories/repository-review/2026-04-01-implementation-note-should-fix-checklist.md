---
date: 2026-04-01
feature: repository-review
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/connectors/spec.md
  - /docs/specs/search-and-docs/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/concepts/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/sync-status/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
  - /docs/decisions/project-memory.md
status: active
---

# Implementation note: should-fix checklist

## Purpose

This note converts the 2026-04-01 repository review into a fix-planning checklist. Each row tells whether the expected repair should be in `code`, `docs`, or `both`.

Interpretation:

- `code`: runtime behavior is wrong and docs already describe the intended behavior well enough
- `docs`: runtime behavior is likely intentional and the spec or durable docs need to catch up
- `both`: the semantics themselves are underspecified or mixed, so code and docs must move together
- `decision`: pick either `code` or `docs` first; the row includes the default recommendation

## Must-fix checklist

| id | priority | item | fix type to choose | recommended default | minimum code scope | minimum docs scope | acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SF-01` | `P1` | Sync Status connector-job reads fail because `ConnectorConnection` is referenced without import. | `code` | `code` | `internal_kb_fullstack/backend/app/services/jobs.py`; add/adjust tests in `internal_kb_fullstack/backend/tests/test_admin_routes.py` and a service-level jobs test | none required beyond optional review note linkback | direct `/v1/jobs` success path works; `list_recent_jobs(..., workspace_id=...)` no longer raises `NameError`; backend tests pass |
| `SF-02` | `P2` | Document reindex excludes `evidence_only` documents by using a member-visible read helper on a write path. | `code` | `code` | `internal_kb_fullstack/backend/app/services/jobs.py`; likely tests around `internal_kb_fullstack/backend/app/api/routes/documents.py` and catalog/jobs services | none if current spec stays | reindex of an `evidence_only` document inside the current workspace succeeds for an authorized actor; route/service tests cover it |
| `SF-03` | `P2` | Durable connector decisions still describe workspace-first connectors as proposed or pending. | `docs` | `docs` | none | `docs/decisions/0005-workspace-data-connectors.md`; `docs/decisions/project-memory.md` | decision docs describe the current live state; no completed migration remains listed as pending |
| `SF-04` | `P2` | `source_url` is used as both external URL and generic source locator. | `both` | `both` | likely `internal_kb_fullstack/backend/app/schemas/documents.py`, read-side serializers, `internal_kb_fullstack/backend/scripts/import_sample_corpus.py`, `internal_kb_fullstack/frontend/app/docs/[slug]/page.tsx`, `internal_kb_fullstack/frontend/components/trust/trust-badges.tsx`, possibly `internal_kb_fullstack/frontend/lib/types.ts` | `docs/specs/system-overview/spec.md`; `docs/specs/search-and-docs/spec.md`; `docs/specs/search-and-docs/contracts.md` | either a split model exists such as URL vs locator, or one field has strict semantics end-to-end; frontend no longer renders non-URL locators as ordinary external links |

## Decision checklist

These are real spec/code drifts, but the right repair depends on product intent. The `recommended default` is what best fits the current repository direction.

| id | priority | item | fix type to choose | recommended default | if you choose code | if you choose docs | acceptance evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `SF-05` | `P2` | `/new`, `/new/manual`, `/new/upload`, and `/new/definition` are `workspace member` only in code, but `authenticated user` in the spec. | `decision` | `docs` | loosen `WorkspaceMemberGuard` usage in `internal_kb_fullstack/frontend/app/new/*.tsx` and align no-workspace handling | update `docs/specs/document-authoring/spec.md` and `docs/specs/document-authoring/contracts.md` to say active workspace member | chosen actor model is consistent across page guards, auth copy, and spec wording |
| `SF-06` | `P2` | Frontend manual/upload authoring omits `visibility_scope`, but the authoring spec still treats it as a write-side input. | `decision` | `code` if manual evidence docs matter; otherwise `docs` | add `visibility_scope` to `internal_kb_fullstack/frontend/lib/types.ts` and `internal_kb_fullstack/frontend/components/editor/document-editor.tsx`; wire upload/manual forms | remove or narrow the visibility claim in `docs/specs/document-authoring/spec.md` and `docs/specs/document-authoring/contracts.md` | chosen contract is explicit and reflected in both form payloads and docs |
| `SF-07` | `P3` | Reindex exists in the backend contract but is not surfaced in the frontend authoring UI. | `decision` | `docs` unless product wants explicit user-facing maintenance | add a frontend API bridge and UI affordance around `POST /v1/documents/{document_id}/reindex` | narrow `docs/specs/document-authoring/spec.md` and `docs/specs/document-authoring/contracts.md` so reindex is backend/operator-only for now | chosen lifecycle surface is consistent across docs and frontend routes |

## Execution order

Recommended order if you want to clear the highest-risk items first:

1. `SF-01` Sync Status runtime fix
2. `SF-02` evidence-only reindex fix
3. `SF-04` provenance contract repair
4. `SF-03` durable connector decision cleanup
5. `SF-05` to `SF-07` authoring contract decisions

## Suggested decision defaults

If you want a concrete default plan without reopening product scope, the lowest-friction path is:

- fix in `code`: `SF-01`, `SF-02`
- fix in `docs`: `SF-03`, `SF-05`, `SF-07`
- fix in `both`: `SF-04`
- decide for `SF-06` based on whether manual `evidence_only` authoring is a real product requirement

## Follow-up use

This note is intended to be the handoff checklist for the next implementation pass. Once you choose the `decision` rows, the implementation work can be split cleanly into:

- runtime fixes
- spec/decision updates
- mixed ontology repairs
