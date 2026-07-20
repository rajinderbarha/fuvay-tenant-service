# Phase 2A Slice 2F-1 — Tenant Engine Mutation Enforcement — Implementation Summary

## Mission
Close the access-scope-aware mutation-enforcement gap for exactly one module,
`app.engines.tenant_engine.router` (27 mutation endpoints), the largest
single module identified by Slice 2F's platform-wide inventory. Unlike Slice
2F (185-endpoint platform scope, honestly reported incomplete), this slice's
narrower scope was fully achievable: **zero unverified mutation endpoints
remain in this module.**

## What changed

### 1. Guard swap (19 endpoints)
`app/engines/tenant_engine/router.py`: swapped `require_permission(P.TENANT_X)`
for `require_tenant_mutation_permission(P.TENANT_X)` on every endpoint reachable
by a tenant-scoped role (not `require_super_admin`-gated, not public). This is
a strict superset of the prior guard — same permission check, PLUS an
access-scope check that rejects any tenant-side user whose `access_scope` is
`customer_support_limited`, regardless of role or permission grants. The
permission argument, the endpoint logic, the service-layer calls, and the
pre-existing `_assert_own_tenant_or_super_admin` tenant-ownership check were
all left untouched.

Of these 19:
- **11** use a permission already granted to `tenant_owner`'s role bundle
  today (`tenant:update`, `tenant:billing:manage`, `tenant:data:export`,
  `tenant:engines:manage` ×6, `tenant:flags:manage` ×2) — these were
  genuinely reachable by tenant-scoped users before this slice, so the guard
  swap closes a real, live gap for them.
- **8** use a permission (`tenant:suspend`, `tenant:reinstate`,
  `tenant:terminate` ×2, `tenant:plan:manage` ×3, `tenant:data:delete`) that
  is **not currently granted to any role** in `ROLE_PERMISSIONS` — only
  `super_admin`'s `P.ALL` wildcard can reach them today. The guard swap has
  zero practical effect on these 8 right now (super_admin is exempt from the
  access-scope check anyway), but is the correct, forward-compatible choice:
  if a future policy change ever grants one of these permissions to
  `tenant_owner`, the access-scope guard is already in place protecting it.
  This gap (permission defined, granted to no role) is a genuine, honestly-
  reported finding of this slice — see `known-limitations.md`.

### 2. `deactivate_staff` session revocation (Workstream 11)
`app/engines/auth/service.py::AuthService.deactivate_staff` previously
revoked only `user_sessions.revoked_at` (DB). `get_current_user` does not
check that column at request time — it checks the Redis flag
`serviceos:session:revoked:{session_id}` instead. This meant an
already-issued JWT for a just-deactivated staff member kept authenticating
until natural expiry. Fixed with the identical pattern Slice 2F already
proved for `update_permissions`: DB revocation + a Redis `setex` flag per
active session (best-effort, logs a warning on Redis failure rather than
raising — matching the codebase's existing fail-open convention elsewhere),
plus `sessions_revoked` in the response and audit metadata.

### 3. Mutation inventory tooling extended (Workstream 12)
`scripts/workflow_rearchitecture/inventory_mutation_routes.py` gained:
- `guard_status(dependency_names)` — classifies a route's guard by its
  dependency name prefix (`require_tenant_mutation_permission`'s inner check
  is renamed `require_tenant_mutation_{perm}`, distinct from plain
  `require_permission`'s `require_{perm}` — confirmed by reading
  `app/core/permissions.py` directly, not assumed).
- `--module <dotted.module.path>` — filters the inventory to one router
  module.
- `--verify-module <dotted.module.path>` — fail-closed mode: exits 1 if any
  matching route's `guard_status` is outside the accepted set
  (`TENANT_MUTATION_PERMISSION_SCOPE_AWARE`, `PLATFORM_ADMIN_ONLY`,
  `PUBLIC_NO_AUTH`), exits 0 otherwise. Run live against
  `app.engines.tenant_engine.router` after the guard swap: **exit 0, 0
  unverified routes out of 27.**

## What did not change (verified, not assumed)
- `PermissionChecker.has()`, `require_permission()`,
  `TENANT_READONLY_ACCESS_SCOPES` — untouched.
- `_assert_own_tenant_or_super_admin` — untouched, still runs in every
  mutation handler, still the tenant-ownership enforcement mechanism.
- The 7 `require_super_admin`-gated onboarding/dunning endpoints — untouched,
  confirmed via `inspect.getsource` regression test.
- `submit_signup` (public) — untouched, confirmed via `inspect.getsource`
  regression test.
- Migration 144 — still unapplied, still at revision 143 (not touched, not
  applied, per the brief's explicit exclusion).
- `readonly@demo-ac-services.local` — not remediated, not queried this slice
  (out of scope; a real read-only test principal was constructed instead,
  never using the live account).
- All previously-approved work listed in the brief (canonical role
  validation, effective-permission wiring, deny-over-grant precedence,
  unknown-permission fail-closed, permission-reduction session revocation,
  seed hardening, authorization integrity checks, invalid-role remediation
  tooling, Technician My Work, ServiceJob Parts restrictions, navigation/
  breadcrumb changes) — none touched.

## Files changed
- **Modified:** `app/engines/tenant_engine/router.py` (19 guard swaps + 1
  import line), `app/engines/auth/service.py` (`deactivate_staff`),
  `scripts/workflow_rearchitecture/inventory_mutation_routes.py` (guard_status
  + module filtering), `tests/test_phase2d_tenant_access_model.py` (updated
  the `require_tenant_mutation_permission` caller-count regression guard from
  2 to 3), `tests/test_phase2f_mutation_enforcement.py` (2 new regression
  tests for the tooling extension).
- **New:** `tests/test_phase2f1_tenant_engine_mutation_enforcement.py` (40
  tests), this documentation directory.

## Alternate-route audit (Workstream 7)
Searched for other registered routes reachable by name that could bypass
this module's newly-guarded actions (suspend/terminate/reinstate/engines/
flags/billing/data-export/delete). Found two candidates, both cleared —
see `tenant-engine-alternate-routes.md` for detail. No bypass found or
required closing.

## Service-layer bypass audit (Workstream 6)
All 19 newly-guarded endpoints call `TenantService` methods that are only
invoked from this router (confirmed via grep for each method name across
`app/`) — no other router or background job calls the same service methods
with a different (weaker) guard in front. See
`tenant-engine-service-bypass-report.md`.

## Test results
40 new tests (`test_phase2f1_tenant_engine_mutation_enforcement.py`), all
passing. Full targeted combined regression suite: **382 passed, 0 failed**
(365 prior + 2 new tooling regression tests in `test_phase2f_mutation_enforcement.py`
+ 40 new Slice 2F-1 tests + the pre-existing `test_final_l5_01b` suite, all
included — see `test-report.md` for the exact command and count reconciliation).

## Disposition
**COMPLETE for this module's scope.** 0 of 27 mutation endpoints remain
unverified. This does not change Slice 2F's platform-wide
`NOT_READY_MUTATION_GAPS` disposition — 18+ other router modules remain
unprotected, exactly as `deferred-items.md` from Slice 2F anticipated this
slice would be the first of several.
