---
date: 2026-03-31
feature: home-navigation-admin
type: implementation-note
related_specs:
  - /docs/specs/home-navigation-admin/spec.md
related_decisions: []
status: active
---

# Account menu action labels stay single-line

## Context

The shared shell account dropdown uses a compact two-button action row for connector access and logout. The shared button primitive is wrap-safe by default, which is correct for dense forms and long CTA copy, but it let short Korean labels such as `연결 소스` and `로그아웃` break across multiple lines inside the account menu.

## Decision or observation

The account dropdown now opts those two actions into `whitespace-nowrap` and allows the row itself to `flex-wrap`. That keeps each control label readable as a single unit while preserving a safe fallback on narrower shell widths.

## Impact

- Header and sidebar account menus keep connector and logout labels on one line.
- If the shell narrows further, buttons wrap as controls instead of breaking text inside the button.
