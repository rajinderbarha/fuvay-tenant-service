# FINAL-L5-04B — Remaining Blockers

> **Updated in FINAL-L5-04C.** Blocker 1 (P0, matching engine) is now closed. Blocker 4 (global active-status) is now closed as a side effect of the new bulk resolver. Remaining blockers are re-numbered and re-prioritized below.

## Closed this sprint (04C)
- ~~Matching engine ignores tenant entitlement~~ — **FIXED**, live and Chromium-proven (see Matching Entitlement Report, Bug Fix Register L5-04C-001).
- ~~Global module/category active-status not layered into entitlement checks~~ — **FIXED as a side effect**: the new `get_entitled_tenant_ids_for_category()` bulk resolver checks `verticals.is_enabled` and `service_categories.is_active` as part of its join, and `has_category_entitlement()` now delegates to it — so both the matching gate and the service-setup guard automatically inherit the global-active check, closing what was previously Blocker 4.
- ~~Customer category availability not entitlement-aware~~ — **FIXED**, inherited automatically from the shared matching pipeline fix, no duplicate logic needed.
- ~~Booking confirmation doesn't revalidate entitlement~~ — **FIXED** (Bug Fix Register L5-04C-002).

## Blocker 1 (P1): No category-level tenant navigation
The tenant portal's sidebar has no category-specific menu items to hide (only module-level gating exists). This is a genuine architectural characteristic of the current tenant-portal nav (flat, generic items), not something fabricated a fix for. See Tenant Navigation Integration Report. Unchanged from 04B — not addressed in 04C (out of this sprint's matching/customer/staff focus).

## Blocker 2 (P1): Only two endpoints have an entitlement guard (`enable_service`, `confirm_draft`)
Service Types, Brands, Issues, Pricing, Coverage, Availability, and Publish Readiness sub-configuration endpoints are still not independently guarded — protected only indirectly via the fact that a service must first be `enable_service`'d. Similarly, the dispatch/staff-routing layer (assigning an already-created job to a specific technician) was investigated this sprint but not wired — the real `jobs` table (`field_ops.Job`) has an ambiguous `service_id`/`service_category` schema with zero real seeded rows to safely verify against, so wiring it was deliberately deferred rather than guessed. The two real gates that matter most (matching and booking confirmation, i.e. where a tenant *becomes* assigned to a category) are now both guarded.

## Blocker 3 (P2): No live cross-tab cache push
An already-open tenant portal tab won't reflect an admin's entitlement change until it remounts. See Cache Invalidation Report. Not applicable to matching/customer availability, which are always server-side-fresh by construction (no cache exists to go stale there).

## Blocker 4 (P2): Admin UI missing several conveniences
No "assign module/category" button, no available-item picker, no confirm-before-disable dialog, no effective-date fields, no per-module category grouping. See Admin UI Report. Unchanged from 04B.

## Blocker 5 (P2): No overlapping-effective-period DB constraint
Two entitlement rows of different statuses could have overlapping `effective_from`/`effective_until` windows; only simultaneous-ACTIVE duplication is DB-prevented. See Automated Validation Report. Unchanged from 04B.

## Blocker 6 (P2): No full empty-database bootstrap re-verification
Migration 132's own up/down was tested; a full from-scratch `alembic upgrade head` from an empty database through all 132 migrations was not re-run this sprint. Unchanged from 04B.

## Blocker 7 (P3): No dedicated staff category-filter surface
Confirmed via dedicated investigation this sprint that no such endpoint exists in this codebase — the practical risk it would protect against is closed upstream (booking confirmation guard), but a redundant staff-side filter/picker itself was not and cannot be built without inventing a new feature outside this sprint's scope. See Staff Entitlement Scope Report.

## Not a blocker (re-confirmed real and working, 04B + 04C combined)
- Data model, migration, DB constraints (partial unique indexes proven at the SQL level).
- Admin API CRUD + audit trail.
- Tenant self-read API, correctly tenant-scoped.
- Module-level tenant nav gating, live-verified.
- Service-setup entitlement guard on the primary gate.
- **Matching engine entitlement enforcement, live and Chromium-proven (04C).**
- **Customer category/provider availability, entitlement-aware via the shared matching pipeline (04C).**
- **Booking confirmation entitlement revalidation guard (04C).**
- Tenant isolation (structural + live-verified, including matching-level isolation as of 04C).
- Admin UI core loop (view/disable/audit/re-enable).
- Backend tests: 0 regressions (verified twice via real before/after diffs), 31 new tests total, 4 real production bugs found and fixed across both sprints.
- Frontend builds: 0 TS errors, both apps build clean.
- Real Chromium E2E: 5/5 passing.
- No N+1 query regression in the new bulk entitlement resolver (dedicated pytest guard).

## Result
0 P0 blockers remain. 2 P1s, 4 P2s, 1 P3 remain, all secondary to the core enforcement guarantee the mission required. See Final Report for the resulting recommendation.
