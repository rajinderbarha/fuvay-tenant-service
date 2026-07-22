# Phase 2A Slice 2F-4 — Highest-Risk Remaining Mutation Module Closure — Implementation Summary

## Mission
Reconcile the global remaining-module inventory, select exactly one
highest-risk module using real security/product risk (not endpoint count),
and fully close it.

## Selected module
`app.engines.tenant_engine.portal_router` — see `selected-module-scope-lock.md`
for the full selection rationale. Ranked highest because it owns
user/staff/session administration (account creation, suspension,
deactivation, lock/unlock, forced session revocation) — the mission's
explicit top-priority risk category — and had zero access-scope protection
today (role-only `require_tenant_owner` gate).

## What changed

### 1. Guard swap (10 endpoints)
Swapped `require_tenant_owner` → `require_tenant_owner_mutation` (the
composed dependency built in Slice 2F-2, reused unmodified) on all 10
mutation endpoints. The 2 GET endpoints that also used `require_tenant_owner`
(`staff_login_history`, `staff_security_status`) were correctly left
untouched — reads don't need the access-scope block.

### 2. Real bug #1 found and fixed: `AuthService` construction crash
`lock_staff`, `unlock_staff`, `revoke_staff_sessions`, and the 2 read-only
security endpoints all constructed
`AuthService(db=db, request_id=..., actor_id=uuid.UUID(user.user_id)...)`
— but `AuthService.__init__` has never accepted an `actor_id` keyword
argument (only `db`, `request_id`, `ip_address`). **All 5 endpoints crashed
with a 500 TypeError on every real call**, discovered only because this
slice's guard-clearing test reached far enough into the handler to hit it.
Fixed by removing the invalid kwarg from all 5 construction sites —
`AuthService`'s relevant methods all take `admin`/target IDs as explicit
call arguments and never read `self.actor_id`.

### 3. Real bug #2 found and fixed: missing session revocation on `deactivate_staff`
Frontend-exposure audit (Workstream 10) revealed the frontend actually
calls `POST /v1/auth/staff/{id}/deactivate` (`app.engines.auth.router`,
`AuthService.deactivate_staff` — already fixed for DB+Redis revocation in
Slice 2F-1), NOT this module's own
`POST /v1/tenant/staff/{id}/deactivate` (`AdminTenantService.deactivate_staff`).
Both routes are live and operate on the same `User` table — a directly-
connected, exploitable weaker alternate route: calling this module's path
directly deactivated a staff member without revoking any of their
sessions. **Fixed**: added the identical DB + Redis session-revocation
pattern to `AdminTenantService.deactivate_staff`, matching
`AuthService.deactivate_staff` exactly.

## Ownership mechanisms confirmed (not modified)
`AdminTenantService._load_tenant_user`/`_load_tenant_staff` (tenant_id
filter) and `AuthService._can_admin_manage_user` (cross-tenant rejection +
tenant_owner-cannot-manage-super_admin) were read and confirmed correct,
pre-existing, and untouched.

## Alternate route confirmed safe
`tenant_engine.admin_router`'s parallel `create_user`/`suspend_user`/
`create_staff`/`deactivate_staff` (same `AdminTenantService`) are
`require_super_admin`-gated — a stronger, platform-only route, not a
bypass, matching every prior slice's precedent for admin-router pairs.

## Closure status
**SECURITY_CLOSED_AND_PRODUCT_POLICY_CLOSED** is not claimed — see below.
**Security**: **SECURITY_CLOSED**. All 10 mutations are access-scope
protected; permissions/tenant/object ownership remain enforced; the one
real directly-connected weaker alternate route found (missing session
revocation) is closed; direct tests pass; 0 unverified routes.
**Product policy**: **BLOCKED** — 7 of 10 endpoints have no confirmed
frontend caller, and their relationship to parallel mechanisms
(`auth.router`'s invite flow) is unresolved (see
`product-decisions-required.md`).

**Final status: SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED.**

## Files changed
- **Modified:** `app/engines/tenant_engine/portal_router.py` (10 guard
  swaps + import + 5 `AuthService` construction crash fixes),
  `app/engines/tenant_engine/admin_service.py`
  (`deactivate_staff` session-revocation fix).
- **New:** `tests/test_phase2f4_tenant_portal_mutation_enforcement.py`
  (35 tests), this documentation directory (15 files).
- **Updated:** global Slice 2F `tenant-mutation-endpoint-inventory.csv`
  (10 rows) and `mutation-enforcement-matrix.csv` (module summary row +
  platform-wide TOTAL row).
- **Unchanged (confirmed):** `tenant_engine.router`, `provider_portal.router`,
  `execution.home_service_router`, `home_service_assignment.staff_router`/
  `.provider_router` — the 5 already-security-closed modules.

## Test results
280 targeted (this slice's family) + 594 (wider targeted combined run) +
226 broader-partition (5 pre-existing skips) — 0 real failures across all
runs.
