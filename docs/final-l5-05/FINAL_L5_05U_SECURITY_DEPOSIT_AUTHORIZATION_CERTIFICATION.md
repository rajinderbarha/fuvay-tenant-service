# FINAL-L5-05U — Security Deposit Permission Namespace, Domain Authorization and Runtime Certification

## Scope actually completed this sprint

FINAL-L5-05O identified that Security Deposit frontend/page permissions
and mutation endpoints used two different permission namespaces, and
applied a bounded fix (granting Finance Admin both) without reconciling
the underlying duplication. This sprint's mission: inventory the entire
domain, select one canonical permission family, migrate everything to it,
retire the alias, and verify runtime behavior across all five Admin
roles. Full evidence in `FINAL_L5_05U_ADR_SECURITY_DEPOSIT_CANONICAL_PERMISSION.md`.

### 1. The true scope was worse than 05O's own framing

Domain inventory found **three** independent, simultaneously-live
Security Deposit endpoint families against the same `SecurityDeposit`/
`SecurityDepositTransaction` tables (not two):

- `finance_hub.admin_router` (`/v1/admin/finance/deposits*`) — the
  richest implementation, `finance:deposits:*` permissions.
- `package_commerce.admin_router` (`/v1/admin/tenants/{id}/security-deposit*`)
  — `finance.security_deposits.*` (a second, independent namespace), zero
  real caller, and a genuine transactional-integrity defect (see below).
- `platform_commerce.router` (`/v1/commerce/tenants/{id}/deposit*`) — the
  real tenant self-service payment flow, gated by `TENANT_BILLING_READ`/
  `MANAGE` (Usage Credit's own permission names, reused for a different
  domain) plus `require_super_admin` (a coarse role check) on its one
  admin-only mutation.

### 2. The precise root cause of the frontend/backend mismatch

A live audit of `/admin/finance/deposits` found the exact mechanism: the
page's nav item AND its page-level `RequirePermission` route guard both
checked the deprecated `finance.security_deposits.read`, while the same
page's own action menu and every backend endpoint it calls checked the
canonical `finance:deposits:*`. No role could both see the page and
successfully use it without holding both namespaces. `admin_readonly`
held only the deprecated alias — could reach the page but its own data
fetch would 403.

### 3. Canonical decision and migration

`FINANCE_DEPOSITS_*` selected as sole canonical family (already the
richest, most-complete, real-caller-backed namespace — no new keys
created, per the mission's own "use existing keys" instruction).
`package_commerce`'s 4 endpoints blocked (410, matching the FINAL-L5-05H
`engine_deduct_wallet` precedent exactly) rather than migrated in place,
since they had zero real caller and a genuine money-tracking defect (see
below). `platform_commerce.admin_adjust_deposit` migrated from
`require_super_admin` to `require_permission(P.FINANCE_DEPOSITS_UPDATE)`
— a real, live bug fix: Finance Admin's own UI rendered this exact
button, but it always 403'd before this sprint.

### 4. Two real, previously-unknown bugs found and fixed as byproducts

**A transactional-integrity defect** (P0, financial correctness):
`PackageCommerceService.admin_refund_deposit`/`admin_forfeit_deposit`/
`admin_mark_deposit_paid` mutated `SecurityDeposit.status` directly with
zero `SecurityDepositTransaction` history row and no call to the shared
`credit_deposit`/`debit_deposit` ledger primitives. Since `current_balance`
is a computed property (`total_paid + replenishment_total - warranty_drawn`),
a "refund" via this path would flip `status="refunded"` while the balance
silently never changed. Confirmed via source read. Closed by blocking the
defective endpoints rather than patching a duplicate implementation —
the canonical `finance_hub` path already does this correctly.

**A cross-tenant vulnerability** (P0, new finding beyond this mission's
literal permission-namespace ask, but squarely within its "verify tenant
isolation" requirement): `CommerceService.get_deposit_status`/
`initiate_deposit`/`get_deposit_transactions` never verified a caller's
own tenant matched the route's `tenant_id`. Gated by `TENANT_BILLING_READ`/
`MANAGE`, which `tenant_owner` legitimately holds for self-service — any
authenticated tenant owner could substitute another tenant's UUID and
read that tenant's deposit status/history. `require_permission()` is pure
RBAC with no tenant scoping, so nothing else caught this. Fixed by adding
`actor_tenant_id` tracking + `_assert_owns_tenant_deposit()` to
`CommerceService`, mirroring `ServiceabilityService._assert_owns_tenant()`'s
established FINAL-L5-05Q pattern exactly — scoped only to
`actor_role == "tenant_owner"`, admin/super_admin callers unaffected.

### 5. Role bundle migration

`admin_finance`: removed all 8 deprecated-namespace grants, kept exactly
the 4 canonical keys (functionally unchanged — the deprecated keys
authorized nothing regardless). `admin_readonly`: migrated from the dead
`FINANCE_SECURITY_DEPOSITS_READ` to canonical `FINANCE_DEPOSITS_READ` — a
real fix, Read Only's existing read-only intent now actually works
end-to-end. `admin_operations`/`admin_security`: confirmed unchanged, zero
deposit permissions.

### 6. Frontend fixes

Nav item, `RequirePermission` page guard, and `permission-catalog.ts` all
migrated to `finance:deposits:read`. Two real, previously-ungated controls
fixed: the deposits list page's Export button (rendered for every role
regardless of `finance:hub:export`, relying solely on backend denial) and
the Tenant Detail page's "Adjust Security Deposit" menu item (rendered
for every role that could reach the page at all, relying solely on the
backend's — now-fixed — permission check). Dead client methods
(`adminTenantApi.getSecurityDeposit`/`markDepositPaid`, targeting the
now-blocked routes) removed.

## Automated guards added

`tests/test_final_l5_05u_security_deposit_permission_authorization.py` —
29 new tests: canonical-namespace verification (deprecated aliases marked
and grep-confirmed to authorize zero live endpoints), frontend/backend
match guards (pinning the exact nav/route-guard/action-menu/catalog bug
found this sprint), role policy matrix (exact-set assertions per role,
zero unexplained cells), the `platform_commerce.admin_adjust_deposit`
migration, the cross-tenant vulnerability fix (3 static + 3 real-Postgres
tests), domain isolation guards (4 tests, 1 real-DB before/after
comparison proving a deposit mutation never touches `tenant_billing`/
`usage_credit_ledger`), and real concurrency (2 concurrent debits against
a shared balance — exactly 1 succeeds, final balance deterministic, never
negative).

`tests/test_phase4_finance_certification.py` — updated in place: the
stale `test_security_deposit_permissions_wired` (asserted the deprecated
namespace was still checked by the router) replaced with
`test_security_deposit_endpoints_are_blocked_410_not_permission_gated`.

`tests/test_sprint4_tenant_onboarding.py` — 3 more dead-handler tests
removed (directly called the now-fully-orphaned `AdminTenantService.
get_security_deposit`/`mark_deposit_paid`, whose routes were already
removed in an earlier "Phase 4 finance certification" sprint; the service
methods themselves are now deleted too).

## Verification summary

- **Backend regression**: full suite `9279 passed, 1 skipped, 0 failed`
  (baseline before this sprint: 9253 passed — net +26 after removing 3
  dead-handler tests and adding 29 new tests).
- **TypeScript**: `0` errors.
- **Live backend startup**: real Postgres + real backend restarted fresh
  with this sprint's code; health check passes.
- **Live 5-role authorization matrix**: Super Admin and Finance Admin —
  list/summary/export all `200`. Operations/Security Admin — `403` on
  list. **Admin Read Only — `200` on list** (previously would have failed
  end-to-end; the real fix confirmed live), `403` on export (correctly
  denied).
- **Live real-bug-fix confirmation**: Finance Admin's `POST
  /v1/commerce/tenants/{id}/deposit/admin-adjust` (the exact button their
  UI renders) returned `200` (previously always `403` under
  `require_super_admin`) — real balance change confirmed
  (`new_balance: 50.0`), then reset.
- **Live blocked-endpoint confirmation**: all 4 `package_commerce`
  security-deposit routes return `410` as expected.
- **Live cross-tenant confirmation**: Super Admin reads both Tenant A and
  Tenant B deposits successfully (unaffected by the ownership fix, as
  intended). The `tenant_owner`-scoped denial itself is proven by the 2
  new real-Postgres automated tests (no `tenant_owner` demo credential was
  available in this session for an end-to-end live HTTP call — the same
  documented limitation pattern used in FINAL-L5-05R/05Q for analogous
  gaps).

## Explicitly not attempted this sprint (honestly documented, not hidden)

See `FINAL_L5_05_BUG_REGISTER.md` (L5-05U-001 through 012) and
`FINAL_L5_05_REMAINING_BLOCKERS.md`. In summary:

- **No Chromium/browser-automation verification was performed** — no
  browser automation tool was available in this session (same limitation
  documented in FINAL-L5-05S/05T). All verification is real, live
  HTTP/API evidence plus real-Postgres automated tests.
- **No responsive/accessibility/performance evidence** — no new frontend
  UI surface was built this sprint (only permission-gating fixes to
  existing controls), so there is no new layout/accessibility surface to
  certify beyond what FINAL-L5-05M/05N already covered platform-wide.
- **Security Deposit settings/configuration** — confirmed genuinely
  absent (the `FINANCE_SECURITY_DEPOSITS_CONFIG_UPDATE` permission was
  defined but never wired to any endpoint anywhere), not built this
  sprint — out of this reconciliation mission's bounded scope ("do not
  redesign the broader Finance UI").
- **`SECURITY_DEPOSITS_RELEASE`/`REVERSE` as distinct operations from
  REFUND** — this codebase does not implement release-without-refund or
  reversal as separate workflows; documented as a scoping decision in the
  ADR, not silently assumed away.

## Result

The mission's core charter — one canonical Security Deposit permission
namespace, migrated everywhere, with the alias frozen and pinned — is
complete and live-verified. The investigation required to get there
surfaced a materially larger problem than FINAL-L5-05O's own framing (3
live implementations, not 2) and 2 real, previously-unknown, independently
serious bugs: a financial transactional-integrity defect and a genuine
cross-tenant read vulnerability. Both are fixed and proven live/real-DB.
Two real frontend controls that previously rendered regardless of the
caller's actual permission are now correctly gated. Zero regressions
across the full 9279-test backend suite. Chromium and
responsive/accessibility/performance evidence remain the honest,
documented gap (no browser tool available; no new UI surface built to
certify).
