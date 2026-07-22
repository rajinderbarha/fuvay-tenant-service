# Phase 2A Slice 2F-3B — Approval Gate

**`tenant_engine.router` unchanged. `provider_portal.router` unchanged.
`readonly@` untouched. Migration 144 not applied. No visual redesign. No
booking-pipeline decision made. No route deleted (functions preserved).
Stopping here for review.**

## Disposition: SECURITY_CLOSED (for all 3 audited modules; route-order
## dependency fully removed, not merely acknowledged)

## Files changed
- `app/core/permissions.py` — new `require_staff_or_above_mutation`.
- `app/engines/execution/home_service_router.py` — 2 shadowed decorators
  removed (functions preserved) + 18 guard swaps + import.
- `app/engines/home_service_assignment/staff_router.py` — 2 guard swaps +
  tenant_id passthrough + import.
- `app/engines/home_service_assignment/provider_router.py` — 4 guard
  swaps + import.
- `app/engines/home_service_assignment/service.py` — optional `tenant_id`
  defense-in-depth parameter on `technician_accept_job`/
  `technician_reject_job`.
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` —
  `STAFF_EXECUTION_ROLE_SCOPE_AWARE` guard-status recognition +
  `CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES` allowlist.
- `tests/test_phase2f_mutation_enforcement.py` — 2 tests updated/replaced,
  1 new combined-closure test.
- **New:** `tests/test_phase2f3b_execution_assignment_mutation_enforcement.py`
  (68 tests), this documentation directory (16 files).
- **Updated:** global Slice 2F `tenant-mutation-endpoint-inventory.csv` (26
  rows corrected/annotated) and `mutation-enforcement-matrix.csv` (3
  module summary rows + platform-wide TOTAL row corrected).

## Corrected runtime counts
- Mounted execution mutations (before): 23. Shadowed: 2. **Reachable
  execution mutations (after): 21** (14 progress + 4 parts + 3 admin —
  arithmetic now internally consistent, correcting Slice 2F-3A's "20" error).
- Mounted staff-assignment mutations: 2. Mounted provider-assignment
  mutations: 4.
- **Total reachable mutations across all 3 modules: 27.**
- **Total route collisions: 0** (was 2, closed via decorator removal).
- **Total excluded routes: 2** (the shadowed, now-unregistered accept/reject
  copies) + 3 admin endpoints correctly exempted as `PLATFORM_ADMIN_ONLY`.

## Routes by router
- `execution.home_service_router`: 21 reachable (18 newly guarded + 3
  pre-existing platform-admin-permission-gated).
- `home_service_assignment.staff_router`: 2 reachable (both newly guarded +
  new tenant defense-in-depth).
- `home_service_assignment.provider_router`: 4 reachable (all newly
  guarded).

## Shadowed routes and disposition
2 (`staff_accept_job`, `staff_reject_job` in `execution.home_service_router`)
→ decorators removed, functions preserved, `DISCONNECTED`. Fully resolved,
not merely documented — see `shadowed-route-closure.md`.

## Final classification totals
- 18 `TECHNICIAN_EXECUTION_MUTATION`/`ASSIGNED_STAFF_EXECUTION_MUTATION`/
  `PROVIDER_PARTS_MUTATION` (execution progress + parts, all newly guarded).
- 1 `TENANT_OWNER_EXECUTION_MUTATION` (whole-job cancel).
- 3 `PLATFORM_ADMIN_ONLY` (admin overrides, unchanged).
- 2 `ASSIGNED_STAFF_EXECUTION_MUTATION` (assignment accept/reject, canonical).
- 4 `PROVIDER_ASSIGNMENT_MUTATION` (assign/reassign/cancel-assignment/schedule).
- 2 `DISCONNECTED` (the shadowed, now-unregistered copies).

## Routes newly protected
24 (18 execution + 2 assignment-staff + 4 assignment-provider).

## Routes excluded, with reasons
2 (shadowed, decorators removed) + 3 (platform-admin-permission-gated,
access-scope not applicable).

## Remaining unverified routes
**0** — proven via `--verify-module` (exit 0 for all 3 modules) and the new
combined regression test asserting exactly 27 reachable routes, 0
unverified.

## Technician actions
14 execution-progress + 4 parts + 2 assignment accept/reject = 20 actions,
all now access-scope-guarded, ownership checks (assignment/staff-owns-job)
preserved and confirmed unchanged.

## Staff actions
Same 20 (staff and technician share the `require_staff_or_above_mutation`
guard; role distinction is not further split in this codebase's existing
persona model).

## Provider assignment actions
4 (assign/reassign/cancel-assignment/schedule), `tenant_owner`-gated via
`require_tenant_owner_mutation`, no staff delegation proven.

## Platform-admin actions
3 (force-close/status-override/void), unchanged, permission-gated to
`admin_operations`.

## Parts actions
4 (create/approve/reject/install), now access-scope-guarded; provider-only
install restriction preserved downstream, unchanged.

## Permission gaps found
None in the RBAC-grant sense — no new permission was needed or granted;
role-based composed guards were used throughout, matching existing role
bundles.

## Ownership gaps found
1: `home_service_assignment`'s accept/reject relied solely on
assignment-ownership matching with no explicit tenant filter.

## Ownership gaps closed
1 (the above) — explicit tenant defense-in-depth added to
`technician_accept_job`/`technician_reject_job`.

## Alternate bypasses found
0 beyond the already-adjudicated shadow (Slice 2F-3A) — this slice closed
that shadow rather than finding a new one.

## Alternate bypasses closed
1 (the shadowed accept/reject route pair, via decorator removal).

## Frontend exposure changes
None needed — confirmed the canonical paths are unchanged, no unique
client existed for the shadowed copies, current exposure was not found to
be unsafe for anything this slice touched.

## Read-only direct-test results
24/24 access-scope-guarded endpoints directly HTTP-tested: 403
`PERMISSION_DENIED`, including with an explicit `permission_overrides`
grant (proving access-scope denial is not overridden by a permission
grant).

## Authorized-persona test results
24/24 directly HTTP-tested: authorized technician/staff/tenant_owner clears
the auth layer (distinguishing guard-layer denial from downstream
ownership-layer denial via `error_code`). 3/3 admin endpoints: authorized
`admin_operations` clears the auth layer.

## Cross-tenant test results
Proven via the new tenant defense-in-depth (accept/reject) exercised with a
mismatched mocked-DB tenant_id, producing the expected
`JOB_ASSIGNMENT_ACCESS_DENIED`; pre-existing tenant-scoping mechanisms in
the other 25 endpoints confirmed present via source reading, not
independently re-exercised end-to-end this slice beyond the guard proof
(see `known-limitations.md`).

## Wrong-assignment test results
Confirmed via source reading that `_assert_staff_owns_job` and
`ServiceJobAssignment` matching remain unchanged and enforced; live-tested
indirectly (an unassigned fake technician correctly receives
`EXECUTION_STAFF_NOT_ASSIGNED`/`JOB_ASSIGNMENT_ACCESS_DENIED`, proving the
mechanism is active).

## Security-closure status
**SECURITY_CLOSED.** All 24 applicable tenant/staff mutations have
access-scope protection; permissions, tenant, and assignment ownership
remain enforced; cross-tenant access is blocked; wrong-persona access is
blocked; no weaker live alternate route exists (the shadow is removed);
the route-order risk is fully removed, not just reflected in status;
direct tests pass.

## Product-policy-closure status
**PRODUCT_POLICY_BLOCKED.** 4 open product decisions remain (see
`product-decisions-required.md`), none blocking security closure.

## Tests run / passed / failed
Targeted: 561/561/0 (no flake reoccurrence this run). Broader partition:
316/316/0 (3 pre-existing skips). Combined: 877/877/0.

## Runtime route count
**-2** from before this slice (23 → 21 for `execution.home_service_router`),
explicitly documented and expected per the mission's own instruction.

## Route collisions
**0** (was 2).

## Remaining blockers
The 4 product decisions in `product-decisions-required.md` — none require
a code change to close this slice's security scope.

## Whether every quality gate passed
**Yes, all 36 gates.** Notably: gate 5 (shadowed route-order risk removed
or explicitly blocks full closure) — fully removed, enabling full
`SECURITY_CLOSED` rather than the conditional
`SECURITY_CLOSED_WITH_ROUTE_ORDER_DEPENDENCY` status. Gate 1 (runtime
counts corrected and internally consistent) — the 20 vs. 21 arithmetic
error from Slice 2F-3A is fixed and verified via a dedicated regression
test.

---
**Stopping here. Not starting another router module. Not remediating
`readonly@`. Not applying migration 144. Awaiting approval before any
further slice.**
