# Deferred Items — Slice 2F

## The core remaining work
Extend access-scope-aware mutation protection from 10 to 185 tenant-facing endpoints, across 24 router modules, one module at a time, each with its own regression proof. Recommended starting order (by risk/value):
1. `tenant_engine.router` (27 endpoints) — largest single module, core business-profile/onboarding/settings domain.
2. `provider_portal.router` (24 endpoints) — team-members/availability/offerings.
3. `execution.home_service_router` (20 endpoints) — but only after resolving the alternate-route overlap with `home_service_assignment` first (see `alternate-route-bypass-report.md`).

## Smaller, scoped follow-ups
1. Add the Redis session-revocation flag to `deactivate_staff` (same 5-line pattern already built for `update_permissions`).
2. Resolve the `execution.home_service_router` vs `home_service_assignment.staff_router`/`provider_router` overlap — determine which is canonical, retire or redirect the other.
3. Individually verify the 83 `UNVERIFIED` (no detected route dependency) endpoints for real in-handler ownership checks vs. genuine gaps.
4. Build the full read-only direct-API test matrix once guards exist to test against.

## Not in scope for any future slice unless separately approved
Admin My Work, Tenant My Work, guided workflows, page consolidation, visual redesign, booking-pipeline work, chat consolidation — none touched, consistent with every prior slice.

## Recommended next slice
Given this slice's exhaustive, real inventory now exists, the highest-value next slice is a single, bounded guard-application pass on **one** router module (e.g., `tenant_engine.router`, the largest) — apply `require_tenant_mutation_permission` or an equivalent to its 27 endpoints, with full regression tests proving tenant_owner success / unauthorized rejection / cross-tenant rejection for each, before moving to the next module. This mirrors exactly how `admin_catalog.tenant_router.py` (the one module already fully protected) was presumably built — incrementally, not all-at-once.
