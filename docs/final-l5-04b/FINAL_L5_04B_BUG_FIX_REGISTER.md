# FINAL-L5-04B — Bug Fix Register

## L5-04B-001: Missing tenant-module entitlement model
- **Severity**: P0 (the sprint's core blocker, carried over from FINAL-L5-04)
- **Evidence**: `tenant.category_id` always NULL for real tenants; no M2M tenant↔module table existed anywhere
- **Root cause**: Never built — only a global (non-tenant-scoped) `verticals`/`vertical_catalog_modules` system existed
- **Files changed**: `alembic/versions/132_tenant_entitlement_architecture.py`, `app/engines/entitlement/models.py`
- **Migration**: 132
- **Fix**: Real `tenant_module_entitlements` table, M2M, with status lifecycle, audit fields, partial unique index
- **Automated tests**: 24 tests in `test_final_l5_04b_entitlement.py`
- **API evidence**: Live curl CRUD cycle (Live API Smoke Report)
- **Browser evidence**: Real Chromium E2E, 3/3 passing
- **Status**: **FIXED**

## L5-04B-002: Missing tenant-category entitlement model
- Same evidence/root-cause class as 001, at the category granularity (`service_groups`).
- **Files changed**: same migration/models file
- **Fix**: `tenant_category_entitlements` table, FK'd to its parent module entitlement row
- **Status**: **FIXED**

## L5-04B-003: Tenant navigation cannot filter by entitlement
- **Severity**: P0
- **Evidence**: `TenantLayout.tsx`'s `NAV_GROUPS` was 100% static, no entitlement-aware filtering existed
- **Root cause**: No entitlement data source existed to filter from (see 001/002)
- **Files changed**: `frontend/tenant-portal/components/layout/TenantLayout.tsx`, `frontend/tenant-portal/lib/api.ts`
- **Fix**: `EntitlementCtx` + `visibleNavGroups` module-level filtering
- **Automated tests**: Real Chromium E2E ("module-level entitlement gating")
- **Browser evidence**: Sidebar `<nav>` scoped assertion, disable→hide→reenable→restore proven live
- **Status**: **FIXED at module granularity; category granularity remains a gap** (no category-specific tenant nav items exist in this codebase's architecture — see Tenant Navigation Integration Report)

## L5-04B-004: Direct routes lack tenant entitlement guard
- **Severity**: P0
- **Evidence**: No backend endpoint checked `tenant_category_entitlements` before this sprint
- **Files changed**: `app/engines/admin_catalog/tenant_service.py` (`enable_service` method)
- **Fix**: Real 403 guard, live-verified positive and negative cases
- **Automated tests**: Fixed 4 regression failures in `test_sprint3_catalog.py` caused by adding this guard (mock fixture `service_group_id` default)
- **API evidence**: Live curl — 403 for non-entitled, 201 for entitled
- **Status**: **FIXED for one endpoint (`enable_service`); broader rollout across all tenant-scoped mutations remains a gap**

## L5-04B-005 / L5-04C-001: Matching engine (and customer availability) ignore tenant entitlement
- **Severity**: P0
- **Evidence**: `select_best_provider()` had no entitlement awareness; a disabled tenant remained matchable
- **Root cause**: The matching pipeline predates the entitlement system entirely and was never wired to it
- **Files changed**: `app/engines/home_service_booking/matching_engine.py`, `app/engines/entitlement/service.py` (new `get_entitled_tenant_ids_for_category` bulk resolver)
- **Fix**: One bulk-resolved entitlement gate applied to the full candidate pool before scoring, with a dedicated `TENANT_CATEGORY_NOT_ENTITLED` exclusion reason
- **Automated tests**: 5 real-database integration tests in `test_final_l5_04c_matching_entitlement.py`, including a dedicated N+1-regression guard
- **API evidence**: Live curl — full disable→exclude→reenable→restore cycle via `/v1/admin/home-services/matching/diagnostics`
- **Browser evidence**: Real Chromium E2E (`final-l5-04c-matching.spec.ts`, 2/2 passing) — same cycle, real browser session
- **Status**: **FIXED** (customer availability inherits the fix automatically since `match_provider_and_price` shares the same matching pipeline — no duplicate logic added)

## L5-04C-002: Booking confirmation trusted a stale match instead of re-validating entitlement
- **Severity**: P1 (window-of-opportunity bug — entitlement could be revoked between match and confirm)
- **Evidence**: `confirm_draft()` transitioned a draft to CONFIRMED using only the earlier match result, with no re-check
- **Root cause**: No revalidation step existed at confirmation time
- **Files changed**: `app/engines/home_service_booking/service.py`, `app/engines/home_service_booking/constants.py` (new `ERR_PROVIDER_ENTITLEMENT_CHANGED`)
- **Fix**: Real-time `has_category_entitlement()` re-check before allowing confirmation; controlled `409 PROVIDER_ENTITLEMENT_CHANGED` instead of a stale success or a 500
- **Automated tests**: 2 real-database integration tests (blocked when disabled, succeeds when still entitled)
- **Status**: **FIXED**

## L5-04B-006 / L5-04C-003: Staff category scope ignores tenant entitlement
- **Severity**: P1 (downgraded from blocking — see resolution below)
- **Investigation (04C)**: A dedicated search for a staff-facing category-filter endpoint found **none exists** in this codebase (`staff_router.py` files only expose "list jobs already assigned to me", no forward-looking category picker).
- **Resolution**: The practical risk (a technician working a job in a non-entitled category) is closed upstream — a new job can no longer be created in a disabled category at all (L5-04C-002's booking-confirmation guard), so there is no non-entitled job for staff to ever be assigned to in the first place.
- **Status**: **Practical risk closed; no distinct staff-side filter surface exists to add a redundant check to** (see Staff Entitlement Scope Report for the full reasoning)

## Additional real bugs found during this sprint's own testing (not in the mission's original list)

### L5-04B-007: `entitlement_audit_log.new_status` VARCHAR(20) overflow on module-disable cascade
- **Severity**: P0 (real 500 error, discovered live)
- **Evidence**: `POST .../modules/home_services/disable` returned `500 INTERNAL_ERROR`; backend log showed `asyncpg.exceptions.StringDataRightTruncationError`
- **Root cause**: Cascade-audit code wrote the 32-character string `"ACTIVE (parent module inactive)"` into a 20-char column
- **Files changed**: `app/engines/entitlement/service.py`
- **Fix**: Keep `new_status` a valid, short status value; move the explanation into `reason`
- **Automated tests**: `TestCascadeAuditColumnLengths` — statically scans for any future hardcoded status string exceeding 20 chars
- **API evidence**: Live curl re-test after fix — 200, no error
- **Browser evidence**: Real Chromium E2E now passes the module-disable step that previously 500'd
- **Status**: **FIXED**

### L5-04B-008: Admin GET entitlements endpoint hid disabled rows
- **Severity**: P1 (usability/correctness — admins couldn't find/re-enable disabled entitlements)
- **Evidence**: After disabling AC & HVAC, the Admin UI's Categories card showed "No category entitlements assigned" instead of the disabled row
- **Root cause**: `resolve_effective_entitlements` always filtered to `effective_only=True`, including for the admin management view (which needs to see everything to manage it)
- **Files changed**: `app/engines/entitlement/service.py`, `app/engines/entitlement/admin_router.py`
- **Fix**: Added `effective_only` parameter, admin router now requests `effective_only=False`
- **Browser evidence**: Real Chromium E2E — disable/re-enable cycle now visible and clickable end-to-end
- **Status**: **FIXED**

### L5-04B-009: `has_category_entitlement` did not cross-reference parent module status
- **Severity**: P1 (correctness — a disabled module wouldn't actually block category-gated actions if the child row's own status was untouched)
- **Evidence**: Found via code review while writing the Module Disable Cascade Policy report, before it could cause a live incident
- **Root cause**: Cascade policy deliberately leaves child category rows' own status unchanged; the enforcement check needed to but didn't look up the parent
- **Files changed**: `app/engines/entitlement/service.py`
- **Fix**: `has_category_entitlement` now joins to `tenant_module_entitlements` and requires the parent to be ACTIVE too
- **Automated tests**: Full suite re-run post-fix, 0 regressions (88/88 in the affected test files)
- **Status**: **FIXED**

### L5-04C-004: `confirm_draft` test regression from the new booking-confirmation guard
- **Severity**: P2 (test-only, no production impact — caught before any commit)
- **Evidence**: `test_confirm_returns_booking_ready_payload` raised `TypeError: object MagicMock can't be used in 'await' expression`
- **Root cause**: The test's `db = MagicMock()` never mocked `db.execute` (not needed before the new guard existed); the guard's new `await self.db.execute(...)` call hit an un-awaitable mock
- **Files changed**: `tests/test_sprint16_home_service_booking.py`
- **Fix**: Mock `db.execute` to return `scalar_one_or_none() -> None`, simulating the real, correct behavior for a synthetic draft whose `offering_id` has no matching `MasterService` row (entitlement check is correctly skipped for offerings with no resolvable group)
- **Automated tests**: Full suite re-run post-fix — confirmed 0 regressions via a real before/after `git stash` diff (90 failed / 42 errors identical both times)
- **Status**: **FIXED**
