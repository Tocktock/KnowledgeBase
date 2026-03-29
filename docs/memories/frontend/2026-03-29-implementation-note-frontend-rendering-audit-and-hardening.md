---
date: 2026-03-29
feature: frontend
type: implementation-note
related_specs:
  - /docs/specs/system-overview/spec.md
  - /docs/specs/home-navigation-admin/spec.md
related_decisions: []
status: active
---

# Frontend rendering audit and hardening

## Context

The current working tree had three repeated frontend failure modes:

- visible/hidden state mismatches in the shared shell and member/admin surfaces
- long text and fixed-grid layouts colliding on laptop and mobile widths
- explicit `force-dynamic` exports spread across the frontend even when the route was already client-driven or could use a narrower fetch boundary

This pass used one defect taxonomy across every current page plus the shared shell:

- display/state bug
- text-fit/overflow bug
- spacing/layout bug
- responsive bug
- rendering/data-loading bug
- interaction/accessibility bug

## Decision or observation

The remediation kept the current product IA and visual language, but hardened the shared primitives and layout rules first:

- the root layout no longer fetches request-time recent-doc data
- recent documents now load inside the client shell
- badges and buttons now allow safe wrapping
- shell nav, account controls, and recent-doc entries now use `min-w-0`, truncation, and mobile overlay dismissal
- dense fixed grids now wait until larger breakpoints before switching to narrow multi-column layouts
- explicit `force-dynamic` exports were removed from frontend routes

## Audit matrix

| Page / surface | Issue | Severity | Root cause category | Intended fix | Verification method |
| --- | --- | --- | --- | --- | --- |
| global shell | account dropdown, nav labels, recent docs, and mobile drawer could overflow or become hard to dismiss | high | display/state bug; text-fit/overflow bug; responsive bug | move recent-doc fetch into client shell, add truncation/`min-w-0`, constrain dropdown width, add mobile overlay | desktop + 390px mobile browser snapshot, typecheck, production build |
| `/` | hero title and side rail cards were too wide for tablet/mobile | medium | spacing/layout bug; responsive bug | reduce headline breakpoint, delay two-column split, ensure card text wraps | desktop + mobile browser snapshot |
| `/login` | invite/reset metadata and CTA rows are dense on small widths, invalid invite/reset states could leak raw JSON error payloads or sit in retry-driven loading loops, and password controls lacked explicit form semantics | high | text-fit/overflow bug; responsive bug; display/state bug; interaction/accessibility bug | rely on wrap-safe buttons/badges, keep two-card stack intact, stop preview retries, normalize preview errors into user-facing copy, and restore labeled form semantics | browser spot check on narrow width |
| `/invite/[token]` | state card needed confirmation that text stays centered and readable on mobile | low | responsive bug | preserve single-column centered card | browser spot check |
| `/connectors` | provider search rows, invite grid, and selected-resource cards were clipping or crowding at laptop widths | high | responsive bug; text-fit/overflow bug | move fixed grids to `xl`, add wrapping/min-width guards for provider/resource labels | desktop + mobile browser snapshot, production build |
| `/search` | filter bar switched to narrow fixed columns too early; result headers squeezed title and metadata together | medium | responsive bug; spacing/layout bug | use stacked/lg grid first, keep result metadata in a shrink-safe secondary column | browser snapshot |
| `/docs` | card titles and slugs could clip inside three-column grids | medium | text-fit/overflow bug | add `min-w-0`, multi-line clamp, wrap-safe title block | browser snapshot |
| `/docs/[slug]` | long titles and source URLs could overflow, and the sidebar became sticky too early | medium | text-fit/overflow bug; responsive bug | reduce mobile heading size, allow URL wrapping, keep sticky behavior at `xl` only | browser snapshot |
| `/new` | editor mode buttons, action rows, and the side rail stacked too late and became crowded | high | responsive bug; spacing/layout bug | move editor side rail to `2xl`, wrap mode buttons and action rows | browser snapshot |
| `/glossary` | CTA card and concept titles needed wrap-safe behavior after moving request intake off-page | medium | text-fit/overflow bug | keep CTA compact and clamp concept titles | browser snapshot |
| `/glossary/requests` | request form and “My requests” cards needed cleaner grid behavior and text wrapping | medium | responsive bug; text-fit/overflow bug | move split form grid to `lg`, wrap concept titles and admin shortcut rows | browser snapshot |
| `/glossary/[slug]` | concept title and support blocks could overflow on narrow screens | medium | text-fit/overflow bug | reduce mobile heading size and preserve wrapped support content | browser snapshot |
| `/glossary/review` | filter grid, candidate list, and detail header were too dense and brittle | high | responsive bug; text-fit/overflow bug | switch fixed filter grid to `xl`, wrap detail header, clamp candidate titles, fetch list client-side | desktop + mobile browser snapshot, production build |
| `/jobs` | full-page request-time render was unnecessary and the page had no client loading state | medium | rendering/data-loading bug | move jobs fetch into a client query with a loading skeleton | browser snapshot, production build |

## Impact

- Frontend routes and shared components now rely on narrower dynamic boundaries and safer wrapping rules.
- The system overview spec now records the shared rendering contract.
- The home/navigation spec now records shell and home responsive behavior as product-level expectations.

## Follow-up

- Keep adding page-specific regression notes here if new rendering defects appear.
- If a future route needs explicit dynamic rendering again, document the reason in the owning feature spec instead of reintroducing it silently.
