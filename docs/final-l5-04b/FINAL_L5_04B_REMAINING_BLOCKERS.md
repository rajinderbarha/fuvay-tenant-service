# FINAL-L5-04B — Remaining Blockers

## Blocker 1 (P0): Matching engine ignores tenant entitlement
Providers are still matched for jobs regardless of whether their tenant's category entitlement is active. See Matching Entitlement Report. **This is the single largest remaining gap** — closing it is the recommended next sprint's primary goal, since Customer Category Availability and Staff Entitlement Scope are both downstream of it.

## Blocker 2 (P1): No category-level tenant navigation
The tenant portal's sidebar has no category-specific menu items to hide (only module-level gating exists). This is a genuine architectural characteristic of the current tenant-portal nav (flat, generic items), not something this sprint fabricated a fix for. See Tenant Navigation Integration Report.

## Blocker 3 (P1): Only one endpoint (`enable_service`) has an entitlement guard
Service Types, Brands, Issues, Pricing, Coverage, Availability, and Publish Readiness sub-configuration endpoints are not independently guarded — they're only protected indirectly via the fact that a service must first be `enable_service`'d (the one guarded gate). A tenant with an already-enabled service prior to entitlement removal could, in principle, still mutate its sub-configuration. Not tested; documented as a real, plausible gap.

## Blocker 4 (P1): Global module/category active-status not layered into entitlement checks
`assign_module_entitlement`/`has_category_entitlement` don't check whether the underlying `verticals.is_enabled` / `service_categories.is_active` global toggle (from FINAL-L5-04) is also true. A tenant could theoretically hold an ACTIVE entitlement for a globally-disabled module.

## Blocker 5 (P2): No live cross-tab cache push
An already-open tenant portal tab won't reflect an admin's entitlement change until it remounts. See Cache Invalidation Report.

## Blocker 6 (P2): Admin UI missing several conveniences
No "assign module/category" button, no available-item picker, no confirm-before-disable dialog, no effective-date fields, no per-module category grouping. See Admin UI Report.

## Blocker 7 (P2): No overlapping-effective-period DB constraint
Two entitlement rows of different statuses could have overlapping `effective_from`/`effective_until` windows; only simultaneous-ACTIVE duplication is DB-prevented. See Automated Validation Report.

## Blocker 8 (P2): No full empty-database bootstrap re-verification
Migration 132's own up/down was tested; a full from-scratch `alembic upgrade head` from an empty database through all 132 migrations was not re-run this sprint (the existing dev DB already had 1–131 applied).

## Not a blocker (re-confirmed real and working)
- Data model, migration, DB constraints (partial unique indexes proven at the SQL level).
- Admin API CRUD + audit trail.
- Tenant self-read API, correctly tenant-scoped.
- Module-level tenant nav gating, live-verified.
- Service-setup entitlement guard on the primary gate.
- Tenant isolation (structural + live-verified).
- Admin UI core loop (view/disable/audit/re-enable).
- Backend tests: 0 regressions, 24 new tests, 3 real production bugs found and fixed this sprint.
- Frontend builds: 0 TS errors, both apps build clean.
- Real Chromium E2E: 3/3 passing.

## Result
1 P0 blocker (matching) prevents a clean `READY_FINAL_L5_04_DYNAMIC_NAVIGATION_CERTIFIED`. See Final Report for the resulting recommendation.
