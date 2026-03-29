---
date: 2026-03-29
feature: frontend
type: implementation-note
related_specs:
  - /docs/specs/connectors/spec.md
  - /docs/specs/glossary-validation/spec.md
  - /docs/specs/document-authoring/spec.md
  - /docs/specs/public-surface-coverage.md
related_decisions: []
status: active
---

# Overview plus deep-link page split

## Context

The first frontend hardening pass improved wrapping and rendering stability, but three surfaces still carried too many workflows in a single page:

- `/connectors` mixed overview, provider OAuth setup, browse/upload selectors, and per-resource management
- `/glossary/review` mixed validation summary, candidate queue, and full per-concept review actions
- `/new` mixed manual authoring, upload-first authoring, and definition-draft generation

That overload made the product harder to learn even after the CSS and rendering fixes.

## Decision or observation

The chosen IA pattern is:

- keep the current sidebar and top-level URLs stable
- turn the top-level route into an overview or chooser surface
- move heavy operator work into deep-link routes instead of adding more sidebar items

The first wave applies that rule to:

- `/connectors` -> `/connectors/setup/[provider]`, `/connectors/[connectionId]`
- `/glossary/review` -> `/glossary/review/[conceptId]`
- `/new` -> `/new/manual`, `/new/upload`, `/new/definition`

## Impact

- The owning specs must treat overview pages and deep-link pages as one feature surface, not as separate navigation products.
- Future dense workflows should prefer the same overview-plus-deep-links rule before adding new global navigation entries.
- Backend contracts remain unchanged for this wave; the split is primarily frontend routing and composition.

## Follow-up

- If Connectors still feels dense after the route split, the next step should be splitting workspace access/invitations out of the overview rather than pushing more setup UI back into `/connectors`.
- If document upload should become a true editable draft flow instead of direct creation, that needs a separate backend-aware follow-up and should not be silently mixed into this split.
