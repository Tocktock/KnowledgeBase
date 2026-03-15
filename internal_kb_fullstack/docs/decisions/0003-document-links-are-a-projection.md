# 0003 - Document links are a projection

## Status
Accepted

## Decision
Internal links are extracted during ingestion and stored in `document_links`.

Backlinks and outgoing links are read from this projection instead of scanning Markdown with regex at query time.

## Why
Regex-scanning every current document for backlink queries was a prototype shortcut.
It mixed content parsing with relation queries and did not scale well.

A projection table makes the domain explicit:
- source document
- source revision
- target slug
- optional resolved target document id
- link order
- optional anchor and link text

## Consequences
- Ingestion updates the link projection.
- Relations become a first-class read model.
- Backlinks are faster and easier to reason about.
- Unresolved links can be exposed later without changing the underlying model.
