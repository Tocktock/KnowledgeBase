# Connectors

## Summary

Connectors import workspace knowledge into a single searchable layer. Workspace sources are the primary path; personal sources remain secondary. Admin UX is template-first and hides raw connector implementation details by default.

## Primary users

- workspace owners and admins who connect shared sources
- members who view shared source status read-only
- individual users who optionally manage personal sources

## Current surfaces and owned routes

- Frontend page:
  - `/connectors`
  - `/connectors/setup/[provider]`
  - `/connectors/[connectionId]`
- Backend public routes:
  - all connector APIs under `/v1/connectors/*`

## Current behavior

- Supported providers are Google Drive, GitHub, and Notion.
- Workspace sources are shared organizational sources.
- Personal sources are user-owned and visually secondary.
- Default workspace sync policy is `auto` every 60 minutes.
- Default personal sync policy is `manual`.
- Provider templates:
  - Google Drive: shared drive, team folder
  - GitHub: repository docs, repository evidence
  - Notion: page, database, export upload
- Default UI hides raw `resource_kind`, `external_id`, and low-level metadata.
- Advanced selection remains admin-only.
- Login continuation always routes anonymous connector actions through `/login` and resumes the provider flow afterward.
- `/connectors` is the overview page. Provider-specific browse, upload, and resource-creation work happens on dedicated setup or connection-detail routes.

## Provider and template model

- Google Drive templates:
  - `shared_drive`
  - `folder`
- GitHub templates:
  - `repository_docs`
  - `repository_evidence`
- Notion templates:
  - `page`
  - `database`
  - `export_upload`

Template intent:

- `repository_docs` and standard Drive/Notion live sources feed member-visible knowledge.
- `repository_evidence` and `export_upload` default to glossary evidence ingestion paths.

## Visibility model

- `member_visible` sources contribute to normal docs, search, concepts, and glossary validation.
- `evidence_only` sources contribute to glossary validation and concept support, but stay hidden from normal member docs and search by default.
- Notion export uploads default to `evidence_only`.
- GitHub repository evidence sources default to `evidence_only`.

## Special source rules

- `export_upload` sources are snapshot uploads, not live connector-syncable sources.
- Uploaded exports can be refreshed only by uploading a new export file.
- The UI must keep upload snapshots on manual sync and disable direct “sync now” actions.
- GitHub docs sync is docs-first. GitHub evidence sync uses text-based repository files for glossary support and excludes binaries and obvious generated or vendor trees by default.
- Workspace-wide validation runs operate on active workspace resources, but snapshot uploads are counted as already-present evidence rather than re-synced live resources.

## Key workflows

- Anonymous connector entry:
  - the user can inspect provider cards and template intent
  - any protected action routes to `/login`
  - successful login resumes the requested provider flow
- Admin live-source setup:
  - start from `/connectors`
  - move into `/connectors/setup/[provider]`
  - complete provider OAuth if needed
  - browse or upload the target source
  - confirm sync and visibility defaults
  - continue resource management on `/connectors/[connectionId]`
- Member view:
  - workspace sources are visible as read-only shared assets
  - personal source management stays separate and secondary
- Evidence-source setup:
  - the admin chooses an evidence template
  - the created resource defaults to `evidence_only`
  - the resource contributes to glossary validation but not default docs/search lists

## Permissions and visibility

- Anonymous users can view the page and templates, but not create or update connections.
- `owner` and `admin` can manage workspace connections and resources.
- `member` can view workspace source status read-only.
- Personal sources are managed only by their owning user.

## Important contracts owned by this spec

- provider readiness contract
- connector connection summary contract
- connector resource summary contract
- browse result contract
- snapshot upload contract
- resource-level sync and visibility update contracts

## Constraints and non-goals

- Connectors remain sync-first rather than query-time tool invocations.
- GitHub v1 is docs-first plus glossary-evidence ingestion. It does not cover issues, PRs, or code search.
- Notion export support is manual upload in v1, not automated export sync.
- Connectors are a source-setup surface, not the place where glossary approval decisions are made.

## Supporting docs

- [`contracts.md`](./contracts.md)
- [`flows.md`](./flows.md)
