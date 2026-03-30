# Intent: Workspace-Bounded Retrieval

## Context

Read-side product surfaces were still effectively global even after workspace auth and connector ownership were introduced.

## Decision

Search, docs list, docs detail, concept grounding, backlinks, and related-document queries now share one resolved workspace boundary. Authenticated viewers use their current workspace, while anonymous read surfaces fall back to the default workspace.

## Rationale

This keeps public read surfaces usable without reintroducing cross-workspace leakage into the search and browsing experience.
