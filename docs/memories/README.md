# Documentation Memories

This folder stores traceable history that should not live in specs or ADRs.

## Purpose

Use `docs/memories/` for:

- conversation outcomes
- intent records
- deprecated content and replacement paths
- rationale behind design and implementation shifts
- implementation notes that explain why a change happened

## Layout

- Organize by feature or functional area.
- Use date-prefixed files:
  - `docs/memories/<feature>/YYYY-MM-DD-<type>-<slug>.md`

## Required metadata

Each memory note must include:

- `date`
- `feature`
- `type`
- `related_specs`
- `related_decisions`
- `status`

## Relationship to other docs

- `docs/specs/` defines current feature behavior.
- `docs/decisions/` defines durable architecture and invariants.
- `docs/memories/` records how and why the current state came to be.
