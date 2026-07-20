# Phase 2A Slice 2F-1 — Approval Gate

> **AMENDED by Slice 2F-1A**: this slice's classification of 8 endpoints
> (suspend/reinstate/terminate ×2/plan-manage ×3/data-delete) as
> `TENANT_OWNER_MUTATION` was corrected to `PLATFORM_ADMIN_ONLY` after
> frontend-exposure evidence showed they are called exclusively by the
> super-admin app, never tenant-portal. The security guard
> (`require_tenant_mutation_permission`) these 8 received here is unchanged
> and remains correct — only the policy label changed. See
> `docs/workflow-rearchitecture/phase-02a-slice-02f1a/approval-gate.md` for
> the amended disposition.

**Booking/job pipelines untouched. No visual redesign. `readonly@` untouched.
Migration 144 not applied. Only `tenant_engine.router` touched — no other
router module. Stopping here for review.**

## Disposition: COMPLETE (for this module's bounded scope)

## Files changed
- `app/engines/tenant_engine/router.py` — 19 guard swaps
  (`require_permission` → `require_tenant_mutation_permission`) + 1 import
  line.
- `app/engines/auth/service.py` — `deactivate_staff` Redis session-revocation
  fix (Workstream 11).
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` — added
  `guard_status()`, `--module`, `--verify-module` (Workstream 12).
- `tests/test_phase2d_tenant_access_model.py` — updated caller-count
  regression guard (2 → 3).
- `tests/test_phase2f_mutation_enforcement.py` — 2 new regression tests.
- **New:** `tests/test_phase2f1_tenant_engine_mutation_enforcement.py` (40
  tests), this documentation directory (11 files).

## Mounted tenant-engine mutation count
27 (unchanged — no route added or removed).

## Classifications
- **19** `TENANT_OWNER_MUTATION` (11 with permission already granted to
  `tenant_owner`; 8 with the permission granted to no role today,
  effectively super_admin-only in practice but still access-scope-guarded
  for forward-compatibility).
- **7** `PLATFORM_ADMIN_MUTATION` (`require_super_admin`-gated onboarding
  review workflow + dunning trigger).
- **1** `FALSE_POSITIVE` (public signup, no auth by design).

## Routes newly protected
19 — every tenant-reachable mutation endpoint in this module now runs
`require_tenant_mutation_permission` instead of bare `require_permission`.

## Routes excluded, with reasons
8 — the 7 `require_super_admin` endpoints (access-scope enforcement not
applicable; super_admin is exempt from that check) and the 1 public signup
endpoint (no authenticated principal exists to have an access_scope).

## Remaining unverified endpoints
**0** — proven live via `inventory_mutation_routes.py --verify-module
app.engines.tenant_engine.router` (exit code 0, `unverified_count: 0` out of
27), and via the new regression test
`test_tenant_engine_router_module_has_zero_unverified_mutation_endpoints`.

## Permission gaps found
8 endpoints use a permission not granted to any role (`tenant:suspend`,
`tenant:reinstate`, `tenant:terminate`, `tenant:plan:manage`,
`tenant:data:delete`) — documented as a product decision in
`deferred-items.md`, not resolved this slice (out of scope: this slice
enforces the *existing* permission model, it does not redesign it).

## Alternate bypasses found / closed
2 candidates found, 0 required closing (both cleared as not-a-bypass — see
`tenant-engine-alternate-routes.md`): `tenant_engine/admin_router.py`'s own
`/suspend` (already `require_super_admin`-gated, same trust level) and
`settings_engine/admin_router.py`'s feature-flag endpoints (different domain
entirely — platform flag definitions, not per-tenant overrides).

## Service-layer bypasses found / closed
0 found. All 19 newly-guarded methods are called from exactly one place
(`tenant_engine.router` itself) — see `tenant-engine-service-bypass-report.md`.

## Read-only direct mutation tests
19/19 endpoints directly HTTP-tested against a read-only test principal
(staff role, valid tenant membership, `access_scope=customer_support_limited`,
plus an explicit permission_overrides grant) — all 19 return 403
`PERMISSION_DENIED`, proving access-scope denial overrides an affirmative
permission grant. Never used the real `readonly@` account.

## Tenant-owner regression tests
4/19 endpoints directly HTTP-tested with an authorized tenant_owner
principal — all clear the auth layer (not 401/403). Representative sample,
not all 19 (see `known-limitations.md` item 3).

## Authorized-staff regression tests
Not separately constructed — this module's 19 endpoints all default to
`TENANT_OWNER_MUTATION` (Workstream 5's instruction: sensitive tenant-
lifecycle/billing/data actions default to owner-only absent existing policy
proving delegation; no staff role in `ROLE_PERMISSIONS` holds any of these
19 permissions today, so there is no authorized-staff persona to test
against for this module specifically).

## Cross-tenant tests
4/19 endpoints directly HTTP-tested — all 4 return 403 via the pre-existing,
unmodified `_assert_own_tenant_or_super_admin` check.

## `deactivate_staff` revocation status
**Fixed.** DB + Redis revocation now both occur, tested (2 new tests: Redis
flag set for every active session; no unnecessary calls when none are
active).

## Targeted tests run / passed / failed
382 / 382 / 0.

## Broader regression coverage
Targeted combined suite only (382 tests) — not claimed as full-repository
coverage, per every prior slice's same honest disclosure.

## Runtime route count
Unchanged (no route added/removed this slice — only dependency swaps).

## Route collisions
0.

## Remaining blockers
None for this module. Platform-wide: 18+ router modules still need the same
treatment (unchanged scope, Slice 2F's finding).

## Whether all quality gates passed
**Yes, for this module's bounded scope.** 0 of 27 mutation endpoints remain
unprotected or unverified — the exact bar Slice 2F-1's brief set as its
completion condition.

---
**Stopping here. Not starting the next router module. Not remediating
`readonly@`. Not applying migration 144. Awaiting approval before any
further guard-application slice.**
