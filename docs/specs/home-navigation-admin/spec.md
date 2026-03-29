# Home, Navigation, and Admin Surfaces

## Summary

The product is framed as a workspace knowledge layer. Navigation and home behavior are role-aware so members focus on finding trusted knowledge, while admins get a separate management layer for sources, QA, and sync health.

## Primary users

- anonymous visitors who need to understand the product and find login
- workspace members who consume knowledge
- workspace owners and admins who need a management layer without exposing operator detail to members

## Current surfaces and owned routes

- Frontend page:
  - `/`
- Shared frontend layout:
  - global app shell and account controls
- Backend public route:
  - `/v1/workspace/overview`

## Current navigation model

- Primary navigation for everyone:
  - Home
  - Search
  - Docs
  - Concepts
- Admin-only manage navigation:
  - Data Sources
  - Knowledge QA
  - Sync Status
- `/new` stays available to authenticated users but is not part of default member navigation.
- Sidebar navigation remains stable. Dense workflows may move into deep-link subpages without adding new main-nav items.

## Route labels

- `/glossary` is the member-facing Concepts surface.
- `/glossary/review` is the admin-facing Knowledge QA surface.
- `/jobs` is the admin-facing Sync Status surface.

## Shared shell behavior

- The global shell must keep navigation, recent documents, account controls, and theme controls visible without overlap across desktop and mobile widths.
- Long names, emails, and document titles in the shell must truncate or wrap safely.
- The mobile sidebar must be dismissible with an overlay and must not leave partially visible controls behind the drawer.

## Home behavior

- Anonymous home explains the product as a workspace knowledge layer and routes users to `/login`.
- Signed-in users without a workspace membership must not be rendered as anonymous visitors. Home shows a dedicated "workspace access required" state instead of the anonymous login CTA.
- Member home prioritizes search, recommended knowledge, and trust signals.
- Admin home includes the member value blocks plus setup and health summaries for sources, sync, and review workload.
- Home CTA rows, summary cards, and side panels must wrap and restack before text clipping on tablet or mobile widths.

## Key workflows

- Anonymous home:
  - explain the product
  - point users to login
  - preview search, synced sources, and concepts
- Member home:
  - surface featured docs and concepts
  - show provenance and freshness inline
  - avoid exposing operator dashboards
- Admin home:
  - include setup state, next actions, source health, sync issues, and validation summary
  - link operators toward `/connectors`, `/glossary/review`, and `/jobs` when action is required

## Access behavior

- Members should not receive the full admin operational UI when they navigate to admin surfaces directly.
- Direct member access to `/connectors`, `/glossary/review`, or `/jobs` should show a clear read-only or unauthorized/admin-only state.
- Auth entry should remain globally visible from shared layout surfaces.

## Important contracts owned by this spec

- workspace overview contract consumed by the home page
- global navigation role and visibility rules
- account-entry behavior for anonymous and authenticated viewers

## Constraints and non-goals

- Normal members should not need to understand jobs, embeddings, or review queues to get value.
- Connectors remain a setup surface, not the main place where glossary judgment happens.
- `/new` remains available, but it is not treated as a primary navigation destination for normal members.

## Supporting docs

- [`contracts.md`](./contracts.md)
- [`states.md`](./states.md)
