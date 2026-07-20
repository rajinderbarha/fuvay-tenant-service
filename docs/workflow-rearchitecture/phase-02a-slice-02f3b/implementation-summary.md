# Phase 2A Slice 2F-3B — Execution/Assignment Mutation Enforcement — Implementation Summary

## Mission
Secure and verify all live mutation routes across
`execution.home_service_router`, `home_service_assignment.staff_router`,
and `home_service_assignment.provider_router`, resolving the shadowed
route-order collision Slice 2F-3A adjudicated but did not fix.

## Corrected runtime counts (Workstream 1)
Slice 2F-3A's deferred summary contained an arithmetic error ("20 live
execution endpoints" vs. "14 progress + 4 parts + 3 admin" = 21). This
slice re-ran the live inventory and confirms:
- **Mounted execution mutations (before this slice): 23**
- **Shadowed execution mutations: 2** (`staff_accept_job`, `staff_reject_job`)
- **Reachable execution mutations (after decorator removal): 21**
  (14 progress + 4 parts + 3 admin — the corrected, internally consistent
  arithmetic)
- **Mounted staff-assignment mutations: 2** (accept, reject — canonical)
- **Mounted provider-assignment mutations: 4** (assign, reassign,
  cancel-assignment, schedule)
- **Total reachable mutations across all 3 modules: 27**
- **Total route collisions (before this slice): 2 → 0 (after)**
- **Total excluded routes: 3** (the 2 shadowed-now-removed + 0 others; the
  3 admin endpoints are not excluded, they're `PLATFORM_ADMIN_ONLY`)

## Shadowed duplicate closure (Workstream 2)
Removed only the `@staff_router.post(...)` decorators from
`staff_accept_job`/`staff_reject_job` in `execution/home_service_router.py`
— the function bodies remain, undeleted. This eliminates the route-order
dependency entirely rather than merely documenting it: OpenAPI now shows
exactly one operation per shared path, and `--verify-overlap` reports 0
overlaps (down from 2). See `shadowed-route-closure.md`.

## Guard composition (Workstream 4)
Two new composed dependencies were added to `app/core/permissions.py`,
reusing the exact pattern `require_tenant_owner_mutation` (Slice 2F-2)
established — no new authorization framework was created:
- **`require_staff_or_above_mutation`**: wraps the existing
  `require_staff_or_above` role dependency (role in `{super_admin,
  tenant_owner, staff, technician}`) with the same
  `TENANT_READONLY_ACCESS_SCOPES` check. Applied to the 18 non-admin
  `execution.home_service_router` endpoints and the 2
  `home_service_assignment.staff_router` accept/reject endpoints.
- Reused **`require_tenant_owner_mutation`** (already existed) for the 4
  `home_service_assignment.provider_router` endpoints (assign/reassign/
  cancel-assignment/schedule) — no staff delegation was proven for these,
  matching `provider_portal.router`'s precedent exactly.

The 3 admin endpoints (`admin_force_close`, `admin_override_status`,
`admin_void`) were left untouched — already correctly gated by
`require_permission(P.ADMIN_JOBS_*)`, granted only to the platform-only
`admin_operations` role, for which a tenant access-scope check is a
category error (same reasoning as `super_admin`'s existing exemption).

## Assignment ownership defense-in-depth (Workstream 6)
`HomeServiceJobAssignmentService.technician_accept_job`/
`technician_reject_job` gained an optional `tenant_id` parameter
(default `None`, non-breaking for any existing caller) that, when
provided, verifies the loaded `ServiceJob`'s tenant matches before
proceeding — explicit defense-in-depth alongside the pre-existing
assignment-ownership check (`ServiceJobAssignment.assigned_staff_member_id`
matching), not a replacement for it. The router now passes
`tenant_id=uuid.UUID(str(user.tenant_id))`. The denial error message is
deliberately generic ("Job not found.") to avoid leaking cross-tenant
record existence.

## Parts/quote boundaries (Workstream 7)
Confirmed unchanged and intact — `PartsRequest` remains `ServiceJob`-only;
no Parts capability exists in `home_service_assignment`; the
provider-only installation restriction is preserved downstream of the
guard swap (untouched).

## Inventory tooling extension (Workstream 14)
`scripts/workflow_rearchitecture/inventory_mutation_routes.py`:
`guard_status()` now recognizes `require_staff_or_above_mutation` as
`STAFF_EXECUTION_ROLE_SCOPE_AWARE` (added to `ACCEPTED_GUARD_STATUSES`);
added `CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES` allowlist for the 3
admin endpoints (permission-gated to a platform-only role, so a tenant
access-scope check doesn't apply, analogous to the existing
`CONFIRMED_FALSE_POSITIVE_ROUTES` pattern).

## Closure status
**SECURITY_CLOSED** (not `SECURITY_CLOSED_WITH_ROUTE_ORDER_DEPENDENCY` —
the route-order risk was fully removed, not merely acknowledged):
- Every live applicable mutation (24 of 27; the 3 admin ones are
  correctly permission-gated platform-only) has access-scope protection.
- Permissions, tenant, and assignment ownership remain enforced.
- Cross-tenant access is blocked (new defense-in-depth for accept/reject,
  pre-existing and confirmed unchanged elsewhere).
- No weaker live alternate route exists (the shadow is removed, not just
  documented).
- Direct tests pass (68 new + 3 updated existing = 71 tests covering this
  slice's scope).

**PRODUCT_POLICY_BLOCKED**: 4 open product decisions remain (see
`product-decisions-required.md`), none blocking security closure.

## Files changed
- **Modified:** `app/core/permissions.py` (new
  `require_staff_or_above_mutation`),
  `app/engines/execution/home_service_router.py` (removed 2 shadowed
  decorators + 18 guard swaps + import), `app/engines/home_service_assignment/staff_router.py`
  (2 guard swaps + tenant_id passthrough + import),
  `app/engines/home_service_assignment/provider_router.py` (4 guard
  swaps + import), `app/engines/home_service_assignment/service.py`
  (optional `tenant_id` defense-in-depth on 2 methods),
  `scripts/workflow_rearchitecture/inventory_mutation_routes.py` (guard
  status + platform-admin-permission allowlist), `tests/test_phase2f_mutation_enforcement.py`
  (3 updated/new regression tests).
- **New:** `tests/test_phase2f3b_execution_assignment_mutation_enforcement.py`
  (68 tests), this documentation directory (16 files).

## Test results
561 targeted (0 failures, no flake reoccurrence) + 316 broader-partition (3
pre-existing skips) = 877 tests, 0 real failures.
