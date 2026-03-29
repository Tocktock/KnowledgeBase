---
date: 2026-03-29
feature: glossary-validation
type: intent
related_specs:
  - /Users/jiyong/playground/KnowledgeHub/docs/specs/concepts/spec.md
  - /Users/jiyong/playground/KnowledgeHub/docs/specs/glossary-validation/spec.md
related_decisions: []
status: active
---

# Manual glossary request intake

## Context

The current product only creates glossary candidates from synced evidence and admin QA actions. That left no supported path for a workspace member to ask for a missing term directly from the Concepts surface.

## Decision

Add a member-facing request flow that creates or updates a suggested concept candidate rather than bypassing admin review. The intake page should live at `/glossary/requests`, while `/glossary` stays focused on approved concept browsing.

## Rationale

- The product still needs admin approval before a term becomes part of the member-facing concept layer.
- A dedicated request page gives the intake workflow room for cleaner UI and a member-facing `My requests` history without crowding the approved Concepts list.
- Using the existing `KnowledgeConcept` model and review queue avoids introducing a second glossary intake system.
- Request metadata must stay attached to the concept so admins can understand who asked for the term and why.
- Manual requests may not have synced evidence yet, so draft generation needs a fallback seeded from the request context.

## Expected workflow

1. A signed-in workspace member submits a term, aliases, and request note from `/glossary/requests`.
2. The backend creates a suggested concept or appends the request to an existing candidate.
3. The same page shows the requester's own glossary requests and the current concept lifecycle/validation state.
4. Admins see the request metadata in `/glossary/review`.
5. Admins create a draft from synced evidence or the stored request context, then approve it through the existing QA path.
