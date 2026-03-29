# Concepts

## Summary

Concepts are the member-facing glossary surface. They expose approved, human-readable term definitions backed by supporting evidence and canonical knowledge documents.

## Primary users

- workspace members who need a trustworthy concept definition
- workspace admins who want to inspect approved outputs without entering the QA workflow

## Current surfaces and owned routes

- Frontend pages:
  - `/glossary`
  - `/glossary/[slug]`
- Backend public routes:
  - glossary read APIs under `/v1/glossary/*`

## Current behavior

- `/glossary` is relabeled as Concepts in the main navigation.
- The list page focuses on consumable approved concepts rather than the operational review queue.
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
- Concept consumption:
  - read the canonical definition
  - inspect supporting evidence and related concepts
  - follow the canonical document link when needed
- Concept-to-doc handoff:
  - concept detail can route the user to the associated document detail page for full context

## Permissions and visibility

- Concepts are member-facing and readable without admin permissions.
- The Concepts surface does not expose the full mutation and review toolset.
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
