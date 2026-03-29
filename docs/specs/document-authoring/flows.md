# Document Authoring Flows

## Manual document creation

1. The authenticated user opens `/new`.
2. The user enters metadata and content.
3. The editor optionally warns about slug conflicts.
4. The frontend submits `POST /v1/documents/ingest`.
5. The user lands on the saved document detail route.

## Upload-assisted drafting

1. The user uploads a supported source file.
2. The backend extracts text and returns draft data.
3. The user edits the draft in the editor.
4. The user saves through the normal ingest route.

## Generated definition draft

1. The user requests `POST /v1/documents/generate-definition`.
2. The backend returns a draft title, slug suggestion, and initial body.
3. The user reviews and edits the draft.
4. The user saves it as a normal document or uses it during glossary QA.
