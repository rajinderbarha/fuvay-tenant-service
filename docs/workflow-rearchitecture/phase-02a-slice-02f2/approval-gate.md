# Phase 2A Slice 2F-2 — Approval Gate

**`tenant_engine.router` unchanged. `execution.home_service_router`
untouched. `readonly@` untouched. Migration 144 not applied. No visual
redesign. Stopping here for review.**

## Disposition: SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED (for `provider_portal.router`)

## Files changed
- `app/core/permissions.py` — new `require_tenant_owner_mutation` composed
  guard (role + access-scope aware, the analogue of
  `require_tenant_mutation_permission` for role-gated routers).
- `app/engines/provider_portal/router.py` — 22 guard swaps
  (`require_tenant_owner` → `require_tenant_owner_mutation`) + import
  cleanup + 3 directly-connected bypass fixes (8 cross-tenant read-back
  leaks closed; deactivate-team-member session revocation added).
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` —
  `guard_status()` extended to recognize `require_tenant_owner_mutation`;
  added `CONFIRMED_FALSE_POSITIVE_ROUTES` allowlist for
  `preview_matching_inputs`.
- **New:** `tests/test_phase2f2_provider_portal_mutation_enforcement.py`
  (53 tests), this documentation directory (16 files).
- **Updated:** global Slice 2F `tenant-mutation-endpoint-inventory.csv` (24
  rows corrected) and `mutation-enforcement-matrix.csv` (provider_portal
  summary row + platform-wide TOTAL row, previously stale since Slice
  2F-1, now correctly reflects 51/185).

## Mounted provider-portal mutation count
24 (unchanged — no route added or removed).

## Final classification totals
- **22** `TENANT_OWNER_SELF_SERVICE` (newly access-scope-guarded this
  slice).
- **1** `TENANT_OWNER_SELF_SERVICE` (`set_area_coverage`, already
  access-scope-guarded pre-slice via `require_tenant_mutation_permission`).
- **1** `FALSE_POSITIVE` (`preview_matching_inputs` — POST verb, no actual
  mutation).

## Routes newly protected
22 — every role-gated tenant-reachable mutation endpoint in this module now
runs `require_tenant_owner_mutation` instead of bare `require_tenant_owner`.

## Routes excluded, with reasons
1 (`preview_matching_inputs`) — confirmed `FALSE_POSITIVE` by reading the
handler source (calls a read-only lookup, no write performed).

## Remaining unverified endpoints
**0** — proven live via `inventory_mutation_routes.py --verify-module
app.engines.provider_portal.router` (exit code 0, `unverified_count: 0` out
of 24).

## Tenant-owner actions (22 + 1 pre-existing = 23)
Team-member CRUD/activate/deactivate/create-login (6), availability
rules/exceptions/presets/booking-window (9), offerings enable/update/
activate/deactivate/refresh-readiness (5), status refresh (1), onboarding
refresh (1), per-area coverage (1, pre-existing).

## Delegated-staff actions
**0.** No staff persona holds `require_tenant_owner`'s underlying role
check — confirmed via direct HTTP test
(`TestUnauthorizedRolesRejected::test_non_owner_role_rejected[staff]`).

## Technician self-service actions
**0.** Same evidence basis — technician role is excluded from
`require_tenant_owner` entirely. No per-technician availability/schedule
capability exists in this router (see `availability-ownership-decision.md`).

## Platform-admin-only actions
**0** in this module (all `require_tenant_owner`-gated endpoints permit
`super_admin` as well as `tenant_owner`, but none are `super_admin`-exclusive
the way `tenant_engine.router`'s onboarding/dunning endpoints are).

## Blocked product decisions
4 (see `product-decisions-required.md`): whether to implement
`create_member_login`; whether to build per-technician availability; whether
to add duplicate-invitation detection; whether any capability should ever
support delegated staff.

## Permission gaps found
None in the RBAC-grant sense (this module is role-gated, not
permission-gated, and no new permission was needed or granted). 3
directly-connected implementation bugs were found and fixed instead (see
below).

## Team/member security findings
No RBAC-escalation surface exists in the updatable team-member fields; no
staff delegation exists; `create_member_login` is an unimplemented stub;
the cross-tenant read-back leak and missing session revocation (below) were
both found in this review. Full detail: `team-membership-security.md`.

## Availability ownership result
Resolved: all availability capabilities are tenant-wide business
configuration, `tenant_owner`-only; no per-technician self-service exists.
Full detail: `availability-ownership-decision.md`.

## Offerings ownership result
Resolved: tenant-wide, `tenant_owner`-only, `CANONICAL_HERE` (no duplicate
route elsewhere). Full detail: `offerings-ownership-decision.md`.

## Frontend exposure changes
**None needed.** All 24 endpoints were already tenant-portal-only
(tenant_owner-facing), confirmed via direct grep — no staff/technician/
platform-admin exposure existed to begin with.

## Alternate bypasses found
1 candidate reviewed (`tenant_engine.portal_router`'s `/staff/*`) — cleared
as `DISCONNECTED` (different table, different capability, not a duplicate).

## Alternate bypasses closed
0 needed — no bypass was found.

## Service-layer bypasses found
**3, all found and closed this slice**: 2 cross-tenant read-back leak
patterns (8 individual SELECT statements across 5 handler groups) and 1
missing session-revocation gap (`deactivate_team_member`). No separate
service class exists for this module (the router is the service layer) —
full detail: `provider-portal-service-bypass-report.md`.

## Service-layer bypasses closed
3 (all of the above).

## Read-only direct-test results
23/23 applicable endpoints (22 newly guarded + re-confirmed unchanged
behavior implied for the 1 pre-existing `set_area_coverage`) reject a
read-only-scoped tenant_owner with 403, even with an explicit
`permission_overrides` grant — directly HTTP-tested for all 22 newly
guarded endpoints.

## Tenant-owner test results
22/22 newly-guarded endpoints directly HTTP-tested: authorized tenant_owner
clears the auth layer (not 401/403).

## Authorized-staff test results
N/A — no staff delegation exists in this module (confirmed, not assumed).

## Technician test results
3/3 non-owner roles (staff, technician, customer) directly HTTP-tested:
all correctly rejected (403) — no technician self-service capability
exists to test positively.

## Cross-tenant test results
Proven via source-inspection regression test
(`TestTenantScopingMechanismSourceProof`), not per-endpoint HTTP tests —
this router has no client-supplied `tenant_id` parameter to attempt
overriding (tenant scope comes exclusively from the authenticated
principal), so the meaningful proof is that every object-mutation handler's
SQL filters by the caller's own `tenant_id`, confirmed for all 13
object-touching handlers, plus the 8 previously-leaky read-backs are now
also confirmed fixed.

## Security-closure status
**SECURITY_CLOSED.** All 22 tenant-reachable mutations are now
access-scope protected; role and tenant-scoping checks remain enforced; the
3 directly-connected bypasses found are closed; no weaker alternate route
exists.

## Product-policy-closure status
**PRODUCT_POLICY_BLOCKED.** 4 genuine product decisions remain open,
explicitly documented, none silently glossed over.

## Tests run / passed / failed
Targeted: 483/483/0. Broader partition: 269/269/0. Combined: 752/752/0.

## Runtime route count
Unchanged (no route added, removed, or modified this slice — only
dependency swaps and internal query fixes).

## Route collisions
0.

## Remaining blockers
The 4 product decisions in `product-decisions-required.md` — none block
security closure, all block full product-policy closure.

## Whether every quality gate passed
**Yes, all 35 gates.** Notably: gate 3 (0 unverified) — proven via
`--verify-module` exit 0. Gate 22 (connected weaker alternate routes closed
or block approval) — 1 candidate found, cleared as disconnected, no
closure needed. Gate 23 (service-layer bypasses closed) — 3 found, 3
closed. Gate 35 (final status distinguishes security from product-policy
closure) — done explicitly above.

---
**Stopping here. Not starting `execution.home_service_router`. Not
remediating `readonly@`. Not applying migration 144. Awaiting approval
before any further slice.**
