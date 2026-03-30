# Intent: Workspace-Safe Ingestion and Slack Readiness

## Context

Connector writes previously fed a global document layer even though authentication and management were already workspace-aware.

## Decision

All connector-driven writes now resolve workspace from the owning connection or resource. Public connector contracts continue to hide `workspace_id`, and Slack remains deferred from runtime routes until the evidence-first ingestion rules are ready.

## Notes

- GitHub repository evidence and Notion export uploads remain `evidence_only` by default.
- Future Slack ingestion is planned as `evidence_only` by default, with promoted summaries as the only path to `member_visible` knowledge.
