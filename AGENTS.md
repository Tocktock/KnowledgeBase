# KnowledgeHub Repository Rules

These rules are top-priority instructions for this repository and must always be followed.

## Documentation governance

1. This project must be developed in a spec-driven manner.
2. Detailed descriptions of project features must live under `/docs`.
3. `/docs` is the Single Source of Truth for feature behavior and requirements.
4. Feature behavior must not be duplicated or redundantly maintained outside `/docs`.
5. Every feature change must update the relevant spec in the same change.
6. Traceability records must be maintained under `/docs/memories`.
7. Conversations, intentions, deprecated content, and rationale behind design or implementation decisions must be recorded in `/docs/memories`.

## Documentation precedence

- Feature behavior and requirements: `/docs/specs/`
- Architectural decisions and durable technical rules: `/docs/decisions/`
- Traceability, rationale history, deprecations, and implementation intent: `/docs/memories/`

Files outside `/docs` may contain short summaries and links, but they must not become shadow Sources of Truth for feature behavior.

## Required workflow

1. Before implementation, create or update the relevant spec under `/docs/specs/`.
2. During design or behavior discussion, record intent and rationale under `/docs/memories/`.
3. After implementation changes, update both the spec and the relevant memory note in the same change.

## Documentation organization

- Use feature-first folders under `/docs/specs/`.
- Use feature-first folders under `/docs/memories/`.
- Use date-prefixed filenames for memory notes: `YYYY-MM-DD-<type>-<slug>.md`.
- Keep new docs in English by default unless a document explicitly needs bilingual content.
