---
date: 2026-04-01
feature: connectors
type: implementation-note
related_specs:
  - /docs/specs/connectors/spec.md
  - /docs/specs/workspace-auth/spec.md
related_decisions:
  - /docs/decisions/0005-workspace-data-connectors.md
  - /docs/decisions/project-memory.md
status: active
---

# Workspace-first connector decision ratification

## Context

The 2026-04-01 repository review found that the live connector model was already workspace-first in specs and storage, but the durable decision layer still described that model as proposed or pending.

## Observation

- Connector specs already define workspace sources as the primary path and personal sources as secondary.
- Workspace-auth already treats `current_workspace_id` and workspace membership as the permission boundary for connector management.
- Persisted connector oauth state and connector connections already attach to a workspace.

## Decision

Ratify the workspace-first connector ADR and update project memory so the durable documentation layer matches the live product and implementation state.

## Impact

- `0005` now reads as an accepted architectural rule instead of an unexecuted migration plan.
- `project-memory.md` now keeps only genuinely pending follow-ups.
- Future connector planning can treat workspace-first ownership as a fixed invariant instead of a roadmap item.
