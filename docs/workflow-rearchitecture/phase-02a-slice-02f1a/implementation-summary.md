# Phase 2A Slice 2F-1A — Tenant Engine Permission-Policy Closure — Implementation Summary

## Mission
Close the policy/classification contradiction Slice 2F-1 left open: 8 of the
19 access-scope-guarded endpoints were labelled `TENANT_OWNER_MUTATION` even
though their permissions are granted to no canonical role (super_admin-only
via the `P.ALL` wildcard). This slice does not change any guard code — it
resolves the classification honestly with evidence, completes the test
matrix Slice 2F-1 left at a representative sample, and documents the
remaining genuine product decisions instead of guessing at them.

## What changed

### Code
**None.** This is a policy-closure and verification slice. No permission was
granted, no guard was added or removed, no endpoint's runtime behavior
changed. `app/engines/tenant_engine/router.py` is untouched since Slice
2F-1.

### Classification correction (Workstream 1/2)
Re-opened the live route inventory (`inventory_mutation_routes.py --module
app.engines.tenant_engine.router`) and cross-referenced every one of the 27
endpoints against: `ROLE_PERMISSIONS` bundle membership, the frontend
exposure audit (which app actually calls each endpoint), and the service
implementation's actual behavior (read directly from
`tenant_engine/service.py`, not inferred from names).

Result: the 8 endpoints previously marked `TENANT_OWNER_MUTATION (permission
not yet granted to any role)` are corrected to **`PLATFORM_ADMIN_ONLY`** —
evidence-based, not name-based:
- `suspend_tenant`, `reinstate_tenant`, `begin_termination`,
  `confirm_termination`, `upgrade_plan`, `downgrade_plan`, `convert_trial`,
  `gdpr_deletion`.
- All 8 are called **exclusively** by `frontend/super-admin/lib/api.ts`,
  never by `frontend/tenant-portal`.
- No permission grant was added. The existing
  `require_tenant_mutation_permission` guard (from Slice 2F-1) is left
  exactly as-is — it is the correct guard regardless of which persona ends
  up authorized, since it's a strict superset of `require_permission`.

The 19 remaining endpoints' classifications are confirmed accurate:
- 11 → `TENANT_OWNER_SELF_SERVICE` (permission genuinely granted to
  `tenant_owner`, genuinely called from `tenant-portal`).
- 7 → `PLATFORM_ADMIN_ONLY` (unchanged, `require_super_admin`-gated
  onboarding/dunning).
- 1 → `PUBLIC_SIGNUP` (unchanged, public).

Full per-endpoint evidence: `tenant-engine-final-policy-matrix.csv`.

### Sensitive capability policy (Workstream 3)
`sensitive-capability-policy.md` reads the actual service implementation for
suspend/reinstate/terminate/plan-manage/data-delete and distinguishes the
sub-behaviors the brief asked about. Two significant, honest findings
emerged that were NOT invented product decisions but discovered gaps in the
existing code:
1. `confirm_termination`'s response claims a "90-day scheduled deletion"
   that no job in the codebase implements.
2. `request_gdpr_deletion` only writes an audit-log row; no anonymization or
   deletion execution mechanism exists anywhere.
Both are escalated in `product-decisions-required.md`, not silently
assumed to work and not fixed this slice (new engineering behavior is out
of scope for a policy-closure slice).

### Frontend exposure audit (Workstream 5)
Confirmed via direct grep of every frontend app: all 8 endpoints have a
real, working caller in `frontend/super-admin`, zero callers in
`frontend/tenant-portal`. No replacement UI was added; no page was
redesigned. Two new regression tests
(`TestNoTenantPortalExposureForPlatformOnlyActions`) guard against future
accidental tenant-portal exposure.

### Complete 19-endpoint test matrix (Workstream 6)
Slice 2F-1 directly HTTP-tested owner-outcome and cross-tenant-outcome for
only 4 of 19 endpoints. `TestFullNineteenEndpointAuthorizationMatrix` (46
new tests) completes this for all 19, split into two evidence-based groups:
- 11 `OWNER_ACCESSIBLE`: owner-clears-auth-layer + cross-tenant-rejected,
  tested per endpoint.
- 8 `PLATFORM_ONLY_VIA_PERMISSION_GAP`: owner-denied-same-tenant (expected),
  owner-denied-cross-tenant, and **super_admin-retains-access** (proving the
  classification correction did not accidentally lock out the actual,
  legitimate caller), tested per endpoint.

## Closure status (Workstream 7)
**`SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED`** for `tenant_engine.router`:
- **SECURITY_CLOSED: yes.** All 19 tenant-reachable mutations remain
  access-scope-protected (unchanged from Slice 2F-1); permissions and
  tenant-ownership checks remain enforced; cross-tenant access is blocked
  (directly proven for all 19 this slice); no weaker alternate route exists
  (re-confirmed, see `tenant-engine-alternate-routes.md`'s addendum).
- **PRODUCT_POLICY_CLOSED: no.** 2 open product decisions remain
  (`voluntary pause` as a distinct feature; a true `subscription
  cancellation` capability) plus 2 open engineering gaps (the missing
  90-day termination-deletion job; the missing GDPR-erasure execution
  mechanism) — all explicitly documented in `product-decisions-required.md`,
  none silently ignored or reported as "no blockers."

## Files changed
- **New:** `docs/workflow-rearchitecture/phase-02a-slice-02f1a/` (10 files).
- **Modified (docs only, no code):**
  `docs/workflow-rearchitecture/phase-02a-slice-02f1/tenant-engine-mutation-inventory.csv`
  (8 rows' classification corrected),
  `tenant-engine-enforcement-matrix.csv` (tested-column updated to reflect
  full 19/19 proof), `tenant-engine-alternate-routes.md` (addendum),
  `deferred-items.md` (2 items marked resolved), `approval-gate.md`
  (amendment banner added);
  `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`
  (8 global rows corrected), `mutation-enforcement-matrix.csv`
  (tenant_engine.router summary row annotated).
- **Modified (tests):**
  `tests/test_phase2f1_tenant_engine_mutation_enforcement.py` — added
  `TestFullNineteenEndpointAuthorizationMatrix` (46 tests) and
  `TestNoTenantPortalExposureForPlatformOnlyActions` (2 tests), 48 new
  tests total, 88 in the file overall.

## Test results
Targeted combined suite: **430 passed, 0 failed** (382 from Slice 2F-1 + 48
new). Broader tenant-lifecycle/onboarding/auth/permission partition (14
additional test files): **364 passed, 5 skipped, 0 failed.**
