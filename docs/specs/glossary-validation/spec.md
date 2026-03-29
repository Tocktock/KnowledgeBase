# Glossary Validation

## Summary

The glossary definition workflow is the primary authoritative output of the product. Workspace sync must end in glossary validation so admins can determine whether a term definition remains correct, needs revision, or needs new supporting evidence.

## Primary users

- workspace owners and admins who operate Knowledge QA
- workspace members who consume approved glossary pages and related concepts

## Current surfaces and owned routes

- Frontend page:
  - `/glossary/review`
- Backend public routes:
  - glossary validation, mutation, and draft APIs under `/v1/glossary/*`

## Current behavior

- Glossary lifecycle status remains separate from validation state.
- Lifecycle statuses include `suggested`, `drafted`, `approved`, `ignored`, and `stale`.
- Validation states include `ok`, `needs_update`, `missing_draft`, `stale_evidence`, and `new_term`.
- Validation metadata includes:
  - `last_validated_at`
  - `validation_reason`
  - `evidence_signature`
  - `last_validation_run_id`
  - `review_required`
- Approved glossary pages stay published even when evidence drifts.
- When evidence drifts, the approved page remains visible, validation moves to `stale_evidence`, and a working draft is created or refreshed for review.
- New terms discovered by sync enter the queue as suggested content and are not auto-approved.

## Validation run modes

- `sync_validate_impacted`: sync active workspace sources and re-check only impacted glossary terms
- `sync_validate_full`: sync active workspace sources and re-check every term
- `validate_term`: re-check one term without a full workspace sync

Workspace-wide runs operate on active connected sources in the current workspace, not every object visible to a provider account.

## Key workflows

- Workspace validation run:
  - resolve active workspace resources
  - sync live resources when the selected mode requires sync
  - skip snapshot uploads for live sync while still including them as evidence
  - evaluate concept evidence and update validation state
  - refresh working drafts for approved terms whose evidence drifted
- Review queue:
  - operators inspect validation counts and latest run summary
  - per-concept rows show lifecycle status, validation state, review reason, support mix, current approved output, and working draft availability
  - operators can approve, ignore, mark stale, split, merge, or request drafts
- Term-specific validation:
  - admins can revalidate a single concept without a workspace-wide sync run

## Knowledge QA workflow

- `/glossary/review` is the primary admin surface.
- Primary admin actions are:
  - `동기화 후 변경분 검증`
  - `동기화 후 전체 검증`
  - `검증만 실행`
  - `이 용어 다시 검증`
- Review detail must show:
  - lifecycle status
  - validation state
  - why the term was flagged
  - support source mix
  - current approved document
  - working draft when present
  - last validation time

## Permissions and visibility

- Knowledge QA is admin-only.
- Members can consume approved concepts, but they do not operate validation runs or glossary mutations.
- Review-required status and evidence drift are operational data points exposed through the admin workflow.

## Important contracts owned by this spec

- glossary refresh contract
- validation-run create/list/detail contracts
- glossary draft generation contract
- glossary mutation contract
- validation-state and run-summary shapes embedded in glossary responses

## Constraints and non-goals

- Validation reuses the existing document store, connector sync jobs, and glossary machinery rather than introducing a second ingestion system.
- Knowledge QA is admin-only. Members consume the approved outputs but do not operate the validation workflow.
- Approved glossary docs are not auto-overwritten when evidence changes.

## Supporting docs

- [`contracts.md`](./contracts.md)
- [`states.md`](./states.md)
