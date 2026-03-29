# Document Authoring Flows

## Manual document creation

1. The authenticated user opens `/new`.
2. The user chooses the manual authoring path and lands on `/new/manual`.
3. The user enters metadata and content.
4. The editor optionally warns about slug conflicts.
5. The frontend submits `POST /v1/documents/ingest`.
6. The user lands on the saved document detail route.

## Upload-assisted drafting

1. The user opens `/new/upload`.
2. The user uploads a supported source file.
3. The upload-specific page isolates file metadata and submission from the manual and definition-first side panels.
4. The backend handles extraction or normalization through the existing upload contract.

## Generated definition draft

1. The user opens `/new/definition`.
2. The user requests `POST /v1/documents/generate-definition`.
3. The backend returns a draft title, slug suggestion, and initial body.
4. The user reviews and edits the draft.
5. The user saves it as a normal document or uses it during glossary QA.
