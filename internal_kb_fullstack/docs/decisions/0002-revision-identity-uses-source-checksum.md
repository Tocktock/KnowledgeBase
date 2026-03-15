# 0002 - Revision identity uses source checksum

## Status
Accepted

## Decision
Revision equality is based on the source checksum (`DocumentRevision.checksum`), not the normalized plain-text hash.

## Why
The previous behavior treated some Markdown structure changes as unchanged when the plain text stayed the same.

That was wrong for this product because these items are part of document meaning:
- wiki links
- heading structure
- markdown blocks
- source formatting that changes link graph or navigation

## Consequences
- `checksum` represents source-level identity.
- `content_hash` still exists, but it is a retrieval/indexing aid, not the primary revision identity.
- If Markdown changes but visible text does not, the system still creates a new revision.
