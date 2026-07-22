# Phase 2A Slice 2F-5A — Package Commerce and Finance Hub Persona Adjudication — Implementation Summary

## Mission
Determine the real persona, capability ownership, and security posture of
`app.engines.package_commerce.admin_router` (20 mutations) and
`app.engines.finance_hub.admin_router` (17 mutations) before any broad
guard application — without assuming `admin_router` naming means
platform-only.

## Central finding
**Both modules are genuinely, evidence-confirmed platform-admin-facing —
the "admin_router" naming was accurate this time**, contrary to the
suspicion motivating this slice. Confirmed via direct role-permission-
bundle inspection (`app/core/permissions.py`), not inferred from names:
- `package_commerce.admin_router`: 15 `PLATFORM_ADMIN_ONLY` + 2
  `ADMIN_FINANCE_ONLY` + 3 `DEPRECATED_410` (intentional dead stubs).
- `finance_hub.admin_router`: 10 `PLATFORM_ADMIN_ONLY` + 7
  `ADMIN_FINANCE_ONLY`.
- **Zero tenant-owner or delegated-finance-staff persona exists in either
  module.**

## The real, substantive finding
23 of the 37 combined mutations use a permission that is defined in
`app/core/permissions.py` but **granted to no role** except via
`super_admin`'s `P.ALL` wildcard:
- `package_commerce.admin_router`: `PACKAGES_CREATE/UPDATE/ARCHIVE/
  ACTIVATE/DEACTIVATE/CLONE` (13 endpoints: package/feature/limit CRUD +
  package purchase).
- `finance_hub.admin_router`: `FINANCE_PAYOUTS_*` (5 endpoints) and
  `FINANCE_CLAIMS_*` (5 endpoints) — including payout approval/processing
  and warranty-claim settlement, the highest real-money-stakes
  capabilities found in either module.

This is not an exploitable security bug (super_admin-only is a secure
disposition) — it is a **product-policy gap**: the platform's own
least-privilege `admin_finance` role (established in a prior slice per
FINAL-L5-05L) cannot currently execute the finance operations its name
suggests it should own. Per the mission's explicit prohibition ("do not
grant new permissions merely to make endpoints reachable"), **no
permission was granted** — the gap is documented and escalated as a
product decision.

## Other findings
- **Security deposit "duplicate"**: `package_commerce.admin_router`'s 3
  deposit endpoints are confirmed already `DEPRECATED_410` (a prior
  slice's fix) — not a live duplicate of `finance_hub`'s canonical
  implementation.
- **Package purchase "duplicate"**: `admin_purchase_package` and
  `package_commerce.tenant_router`'s `tenant_purchase_package` both call
  the identical `create_package_assignment` service method — a
  legitimately shared canonical write, not two competing owners.
- **Credit wallet**: confirmed to delegate entirely to the canonical
  `UsageCreditService` (per the FINAL-L5-05J historical fix) — no direct
  balance overwrite found. One non-blocking observation: top-up
  idempotency only works if the caller explicitly supplies a key.

## No code change made
Per Workstream 11's 7-point test, no finding conclusively met the bar for
a safe, scoped code fix this slice — the substantive finding
(permission-bundle gap) requires a product decision (who should approve
real-money payouts?), which the mission explicitly excludes from this
slice's authority. **No permission was granted, no guard was applied, no
model was merged.**

## Module readiness
Both modules: `READY_FOR_PLATFORM_ADMIN_GUARD_VERIFICATION` — neither
needs a tenant-mutation-guard-application slice (no tenant persona
exists in either). **Selected for the next slice**:
`app.engines.finance_hub.admin_router`, on the strength of its higher
real-money stakes (payout/claims) — but that next slice is a
product-decision-and-verification slice, not a broad guard-application
slice in the style of 2F-1 through 2F-4.

## Files changed
- **New:** `tests/test_phase2f5a_finance_persona_adjudication.py` (13
  tests), this documentation directory (18 files).
- **No application code was changed** — `app/engines/package_commerce/`
  and `app/engines/finance_hub/` are byte-for-byte unchanged from before
  this slice. `app/core/permissions.py` was read, not modified.
- **Global Slice 2F CSVs**: not updated — no classification in the global
  inventory changed as a result of this slice (neither module was
  previously listed with an inaccurate classification requiring
  correction; `package_commerce.tenant_router` was already correctly
  distinct from `package_commerce.admin_router` in the existing
  inventory).

## Test results
293 targeted (Slice 2F family) + 614 broader finance partition (4
pre-existing skips) = 907 tests, 0 real failures.
