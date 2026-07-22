# Next-Slice Scope Lock — finance_hub.admin_router

## Selected module
`app.engines.finance_hub.admin_router`.

## Why selected
See `module-readiness-decision.md` — highest real-money stakes among
remaining findings (payout approval/processing, warranty-claim
settlement), currently reachable only by `super_admin` due to a
permission-bundle gap (`FINANCE_PAYOUTS_*`/`FINANCE_CLAIMS_*` granted to
no role).

## Runtime mutation count
17 (confirmed live).

## Highest-risk endpoints
1. `POST /v1/admin/finance/payouts/{payout_id}/approve` — approves a real
   provider payout.
2. `POST /v1/admin/finance/payouts/{payout_id}/mark-completed` — marks a
   payout as completed.
3. `POST /v1/admin/finance/warranty-claims/{claim_id}/settle` — settles a
   warranty claim (likely triggers payment/credit).

## Known alternate routes
None found — `finance_hub.admin_router` is the sole implementation for
deposits, payouts, top-up refunds, and warranty claims.

## Expected personas
`admin_finance` (platform finance role) and `super_admin`. No tenant_owner
or delegated-staff persona applies.

## Expected permissions
The EXISTING permission constants (`FINANCE_PAYOUTS_APPROVE`,
`FINANCE_PAYOUTS_COMPLETE`, `FINANCE_PAYOUTS_PROCESS`,
`FINANCE_PAYOUTS_REJECT`, `FINANCE_CLAIMS_APPROVE`, `FINANCE_CLAIMS_ASSIGN`,
`FINANCE_CLAIMS_REJECT`, `FINANCE_CLAIMS_SETTLE`) already exist and are
already correctly checked by the router — the open question is purely
which role(s) should be granted them, a product decision this slice
explicitly did not make.

## Expected access-scope behavior
None needed — `admin_finance`/`super_admin` are platform roles with no
tenant `access_scope` concept, consistent with every other platform-only
module closed in this series.

## Explicitly excluded
`package_commerce.admin_router` (deferred, not investigated further this
slice beyond the adjudication already completed) and all 6 previously
security-closed tenant-facing modules.

## What the next slice should NOT do
Grant the permissions without an explicit product decision first;
broadly apply tenant-mutation guards (none apply); redesign the payout or
warranty-claim workflow; add new payment-gateway behavior.
