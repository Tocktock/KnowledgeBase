# Document Authoring

## Summary

Document authoring is the manual fallback path for knowledge that does not yet exist in synced sources or that needs a human-authored canonical page. It is available to authenticated users, but it is not part of the default member navigation.

## Primary users

- authenticated users who need to create or update a manual knowledge page
- workspace admins who create or refresh canonical definition pages during glossary QA

## Current surfaces and owned routes

- Frontend page:
  - `/new`
- Backend public routes:
  - write-side document APIs under `/v1/documents/*`

## Current behavior

- `/new` opens a Markdown-capable editor with structured metadata fields.
- Users can:
  - create a manual document directly
  - upload a file and convert it into a document draft
  - generate a definition draft from existing support evidence
  - reindex an existing document after changes
- The editor supports visual editing, source editing, and preview workflows.
- Slug conflicts are handled explicitly rather than silently overwriting the existing document.
- Authoring remains secondary to synced-source ingestion in the overall product positioning.

## Key workflows

- Manual create:
  - enter document metadata and Markdown content
  - submit ingest request
  - receive canonical document summary and slug
- Upload:
  - upload a supported file
  - backend extracts or normalizes content
  - editor proceeds with the resulting draft
- Definition draft generation:
  - request a generated definition draft from existing concept or support context
  - review and edit the generated content before saving
- Reindex:
  - trigger reindex for a document after content changes

## Permissions and visibility

- `/new` is intended for authenticated users.
- Newly authored documents can set visibility through the write-side request contract.
- Manual documents can become canonical concept documents and therefore appear in Concepts and Search once they are member-visible.

## Important contracts owned by this spec

- ingest request and document write response contracts
- upload contract
- definition draft generation contract
- document reindex contract

## Constraints and non-goals

- `/new` is not the product’s primary entry point.
- This spec covers manual creation workflows, not read-side document browsing and trust presentation.
- Generated drafts must still be reviewed by a human before being treated as canonical knowledge.

## Supporting docs

- [`contracts.md`](./contracts.md)
- [`flows.md`](./flows.md)
