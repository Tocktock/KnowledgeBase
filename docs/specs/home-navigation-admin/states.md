# Home and Navigation States

## Anonymous

- Home explains the workspace knowledge layer.
- Header and sidebar expose login entry.
- Manage navigation is hidden.

## Signed In, No Workspace

- The account surface shows the authenticated user.
- Home must not render the anonymous marketing CTA.
- Home explains that the user needs a workspace invite or membership before workspace-specific search and knowledge surfaces become active.

## Member

- Primary navigation shows Home, Search, Docs, and Concepts.
- Manage navigation is hidden.
- `/connectors`, `/glossary/review`, and `/jobs` do not expose full operator tooling.

## Owner/Admin

- Primary navigation remains the same as for members.
- Manage navigation adds Data Sources, Knowledge QA, and Sync Status.
- Home adds setup health and validation summary blocks.

## Auth surface

- Anonymous state shows `로그인`.
- Authenticated state shows a compact account surface with workspace context.
- Login continuation preserves route and post-auth parameters where relevant.
