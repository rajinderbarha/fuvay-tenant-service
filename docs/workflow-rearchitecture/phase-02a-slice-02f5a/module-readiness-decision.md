# Module Readiness Disposition — Workstream 12

## package_commerce.admin_router
**Disposition: `READY_FOR_PLATFORM_ADMIN_GUARD_VERIFICATION`**

Reasoning: every one of the 20 mutations is genuinely platform-facing
(15 `PLATFORM_ADMIN_ONLY`, 2 `ADMIN_FINANCE_ONLY`, 3 `DEPRECATED_410`) —
confirmed via role-permission-bundle inspection, not inferred from
naming. No tenant-owner or delegated-staff persona exists. This module
does NOT need a `require_tenant_mutation_permission`-style guard-
application slice (there is no tenant persona to guard against) — the
"verification" work remaining is confirming/deciding whether
`PACKAGES_*` should be granted to `admin_finance` (a product decision, not
a code task).

## finance_hub.admin_router
**Disposition: `READY_FOR_PLATFORM_ADMIN_GUARD_VERIFICATION`**

Reasoning: same structural conclusion — all 17 mutations are platform-
facing (7 `ADMIN_FINANCE_ONLY`, 10 `PLATFORM_ADMIN_ONLY` via the
permission-bundle gap). No tenant-owner or delegated-staff persona exists.
The remaining work is the same class of product decision: should
`FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` be granted to `admin_finance`?

## Why neither module needs a broad tenant-mutation-guard slice
Unlike every module closed in Slices 2F-1 through 2F-4 (`tenant_engine.router`,
`provider_portal.router`, `execution.home_service_router`,
`home_service_assignment.*`, `tenant_engine.portal_router`), which all had
a genuine `tenant_owner`/staff/technician persona reachable via a role or
permission grant, **neither `package_commerce.admin_router` nor
`finance_hub.admin_router` has any tenant-scoped persona at all** — every
reachable route (except the 3 dead stubs) requires either `super_admin`
directly or a permission exclusively granted to `admin_finance`/
`super_admin`. Applying an access-scope guard to a route with no tenant
persona would be a category error, not a security improvement.

## Selected next module
**`app.engines.finance_hub.admin_router`** is selected for the next slice,
per the mission's requirement to select exactly one. Chosen over
`package_commerce.admin_router` because:
- **Higher financial-integrity risk**: its blocked capabilities (payout
  approval/processing, warranty-claim settlement) represent real-money
  movement (`REAL_MONEY_PAYMENT`, per `money-credit-boundary.md`), versus
  `package_commerce`'s blocked capabilities (package catalog CRUD), which
  are definitional, not transactional.
- **Larger proportion of the module affected**: 10 of 17 routes (59%)
  versus 13 of 20 (65% — comparable, but lower absolute stakes per route).
- **Clearer, narrower next step**: a single product decision (grant
  `FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` to `admin_finance`, yes or no)
  versus `package_commerce`'s broader `PACKAGES_*` question spanning
  catalog definition, purchase, and lifecycle management.

**Important caveat, stated explicitly**: the "next slice" for
`finance_hub.admin_router` is **not** a broad tenant-mutation-guard
application slice in the style of Slices 2F-1 through 2F-4 — there is no
tenant persona to guard. It is a **product-decision-and-verification
slice**: resolve whether `admin_finance` should hold
`FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*`, then (if granted) verify the
existing guards correctly enforce the decision — see
`next-module-scope-lock.md`.
