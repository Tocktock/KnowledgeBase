# Decisions and Project Memory

This folder stores architectural decisions and durable project memory.

## Current decisions

- [0001 - Canonical write boundary](./0001-canonical-write-boundary.md)
- [0002 - Revision identity uses source checksum](./0002-revision-identity-uses-source-checksum.md)
- [0003 - Document links are a projection](./0003-document-links-are-a-projection.md)
- [0004 - One active embedding profile per deployment](./0004-one-active-embedding-profile-per-deployment.md)
- [project-memory](./project-memory.md)

## How to use this folder

- Add a new numbered file for any lasting architectural choice.
- Update `project-memory.md` when an invariant or operational rule changes.
- Prefer writing down *why* a rule exists, not just *what* it is.
