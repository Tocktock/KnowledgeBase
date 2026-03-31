# Document Authoring

## Summary

Document authoring is the manual fallback path for knowledge that does not yet exist in synced sources or that needs a human-authored canonical page. It is available to authenticated users, but it is not part of the default member navigation.

## Primary users

- authenticated users who need to create or update a manual knowledge page
- workspace admins who create or refresh canonical definition pages during glossary QA

## Current surfaces and owned routes

- Frontend page:
  - `/new`
  - `/new/manual`
  - `/new/upload`
  - `/new/definition`
- Backend public routes:
  - write-side document APIs under `/v1/documents/*`

## Current behavior

- `/new` is a chooser page for the available authoring modes.
- `/new/manual` opens the Markdown-capable editor with structured metadata fields.
- `/new/upload` isolates the file-upload-first flow from the rest of the authoring UI.
- `/new/definition` isolates the definition-draft generation flow from the rest of the authoring UI.
- Users can:
  - create a manual document directly
  - upload a file and convert it into a document draft
  - generate a definition draft from existing support evidence
  - reindex an existing document after changes
- Manual and upload-backed authoring may capture optional source metadata, but stored provenance is normalized into the shared `source_url := https | generic | null` contract.
- The editor supports visual editing, source editing, and preview workflows.
- Slug conflicts are handled explicitly rather than silently overwriting the existing document.
- Authoring remains secondary to synced-source ingestion in the overall product positioning.

## Key workflows

- Manual create:
  - start at `/new` or go directly to `/new/manual`
  - enter document metadata and Markdown content
  - submit ingest request
  - receive canonical document summary and slug
- Upload:
  - start at `/new/upload`
  - upload a supported file
  - backend extracts or normalizes content
  - the flow stays isolated from the manual and definition-first side panels
- Definition draft generation:
  - start at `/new/definition`
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
