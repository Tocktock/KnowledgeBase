# Concepts

## Summary

Concepts are the member-facing glossary surface. They expose approved, human-readable term definitions backed by supporting evidence and canonical knowledge documents.

## Primary users

- workspace members who need a trustworthy concept definition
- workspace admins who want to inspect approved outputs without entering the QA workflow

## Current surfaces and owned routes

- Frontend pages:
  - `/glossary`
  - `/glossary/requests`
  - `/glossary/[slug]`
- Backend public routes:
  - glossary read APIs under `/v1/glossary/*`

## Current behavior

- `/glossary` is relabeled as Concepts in the main navigation.
- The list page focuses on consumable approved concepts rather than the operational review queue.
- `/glossary` links to a dedicated request page instead of embedding the intake form directly in the approved-concepts list.
- Signed-in workspace members can submit a new concept request and review their own request history from `/glossary/requests` when the term does not exist yet.
- Concept requests do not publish immediately. They create or update a suggested concept candidate that admins review in Knowledge QA.
- Concept detail exposes:
  - lifecycle status where relevant to the view
  - support evidence
  - canonical document or generated definition link
  - related concepts
  - trust and source information for supporting evidence
- Evidence-only sources can contribute support evidence, but the concept surface is still a member-facing read surface rather than an operational dashboard.

## Key workflows

- Concept discovery:
  - browse or search approved concepts
  - open a concept detail page
- Concept request intake:
  - authenticated workspace members can propose a new term, aliases, and request context from the dedicated Concepts request page
  - members can also see their own existing requests and the current concept lifecycle/validation state for each one
  - the request is queued for admin review instead of bypassing the glossary approval workflow
- Concept consumption:
  - read the canonical definition
  - inspect supporting evidence and related concepts
  - follow the canonical document link when needed
- Concept-to-doc handoff:
  - concept detail can route the user to the associated document detail page for full context

## Permissions and visibility

- Concepts are member-facing and readable without admin permissions.
- The Concepts surface does not expose the full mutation and review toolset.
- Request submission requires authentication plus an active workspace membership.
- Validation state may influence what support context is shown, but the operational actions remain owned by the glossary-validation feature.

## Important contracts owned by this spec

- glossary concept list and concept detail contracts
- glossary support item contract
- concept-facing trust and canonical-document link behavior

## Constraints and non-goals

- This surface is not the admin review queue.
- Concepts consume approved or otherwise published concept state; they do not decide lifecycle or validation status.
- Mutation routes in the glossary module are documented under glossary validation, not here.

## Supporting docs

- [`contracts.md`](./contracts.md)
