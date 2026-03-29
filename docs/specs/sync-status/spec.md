# Sync Status

## Summary

Sync Status is the admin-facing operational surface for job and readiness health. It exists to support the glossary-first knowledge workflow, not to become the main member experience.

## Primary users

- workspace owners and admins who monitor sync queues, failures, and readiness

## Current surfaces and owned routes

- Frontend page:
  - `/jobs`
- Backend public routes:
  - `/v1/jobs*`
  - `/healthz`
  - `/readyz`

## Current behavior

- `/jobs` is labeled as Sync Status in navigation.
- The page is admin-only and wrapped in the same manage-access guard as other operator surfaces.
- The page summarizes:
  - queued jobs
  - processing jobs
  - failed jobs
  - recent job history
- Health and readiness routes remain low-level service endpoints rather than end-user product pages.

## Key workflows

- Admin health inspection:
  - inspect current queue pressure
  - check failed or slow jobs
  - correlate source health with validation or sync issues
- Service health:
  - use `/healthz` for liveness
  - use `/readyz` for readiness and deployment health

## Permissions and visibility

- `/jobs` is restricted to workspace admins.
- Health and readiness endpoints are public service endpoints, but they are not a replacement for the admin UI.

## Important contracts owned by this spec

- job list and job detail contracts
- health and readiness contracts

## Constraints and non-goals

- Sync Status is a support surface, not the main glossary decision surface.
- Members should not need to interpret queue internals to consume knowledge successfully.

## Supporting docs

- [`contracts.md`](./contracts.md)
