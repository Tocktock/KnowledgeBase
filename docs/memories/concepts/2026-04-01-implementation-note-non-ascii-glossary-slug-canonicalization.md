---
date: 2026-04-01
feature: concepts
type: implementation-note
related_specs:
  - /docs/specs/concepts/spec.md
  - /docs/specs/concepts/contracts.md
related_decisions: []
status: active
---

# Implementation note: non-ASCII glossary slug canonicalization

## Context

The member-facing glossary detail page began using a canonical-slug redirect after glossary public slugs were stabilized. Next route params for non-ASCII slugs can arrive percent-encoded, while the glossary API returns the decoded canonical slug.

## Change

The glossary detail page now decodes the route param before detail lookup and before comparing it to the canonical slug returned by the API. Shared frontend path-segment helpers also normalize slug-based proxy routes so encoded and already-encoded inputs resolve to the same backend path.

## Result

Clicks on glossary concepts with Korean or other non-ASCII slugs no longer enter a self-redirect loop, and the canonical detail page renders normally.
