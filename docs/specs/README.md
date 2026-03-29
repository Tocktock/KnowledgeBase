# Feature Specs

This folder contains the canonical Source of Truth for feature behavior.

## Layout

- One feature folder per product area.
- The canonical entry file is always `spec.md`.
- `contracts.md` is required when the feature owns backend public routes or non-trivial request/response contracts.
- `flows.md` or `states.md` is optional and should exist only when the feature has meaningful state transitions or role-dependent workflows.
- Optional supporting files may live beside `spec.md`, but `spec.md` remains the primary feature reference.

## Naming

- Folder name: short, stable, feature-first
- Canonical file: `docs/specs/<feature>/spec.md`
- Contract file: `docs/specs/<feature>/contracts.md`
- Optional state or flow file: `docs/specs/<feature>/states.md` or `docs/specs/<feature>/flows.md`

## Minimum content

Each spec should describe:

- feature purpose
- primary users
- key workflows
- permissions or visibility rules
- important public interfaces or APIs
- non-goals or constraints where they prevent implementation mistakes

Each `contracts.md` should describe:

- route and method
- purpose
- caller and role requirements
- query parameters or request body
- response shape or canonical schema module
- important error states
- a minimal example when the route is non-trivial

The truth target is the current working tree. Specs should reflect the live product behavior and public contracts currently represented in source, even if the worktree is ahead of the last clean commit.

## Maintenance rule

Any change to feature behavior must update the corresponding `spec.md` in the same change.
