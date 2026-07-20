# Deferred Items — Slice 2F-22

| Item | Reason deferred | Next step |
|---|---|---|
| Wire Razorpay initiate/confirm to `ServicePackage` purchases | New payment infrastructure explicitly out of scope; requires checkout/refund product decisions | Dedicated payment slice — `product-decisions-required.md` #1 |
| Partial unique index for the duplicate-pending race | Requires a migration; prohibited | Migration-enabled slice — #2 |
| Package eligibility controls (`is_purchasable`, tenant-private, vertical, availability window) | Would be invented policy; prohibited | Product decision — #3 |
| Renewal / upgrade / stacking / replacement semantics | Explicitly prohibited from invention | Product decision — #4 |
| Refund and reversal path | No mechanism exists; policy undefined | Product decision — #5 |
| `staff` purchase permission | Would require a new permission; prohibited | Product decision — #6 |
| Free-package immediate activation | Deliberately not added — auto-activation is where payment assumptions turn dangerous | Product decision — #7 |
| Enforce Razorpay configuration in production | `platform_commerce` domain, pre-existing, unaffected here | Platform decision — #8 |
| Remove dead `purchase_package` / `TenantPackagePurchase` | Cleanup, out of scope; legacy tests still reference it | Cleanup slice — #9 |
| Read-only UI gating audit of the tenant portal | Frontend work prohibited; backend control is load-bearing and in place | Frontend slice |
| Live two-session concurrency tests | No database in this environment | Run where a live DB exists |
| Slice-2D canary tests | Explicitly prohibited from rewriting this slice | Requires revisiting `tenant-readonly-decision.md` |

## Remaining authorization queue

8 modules / 19 routes remain unprotected — see
`remaining-module-queue-update.csv`. No module was selected or begun; module
selection is the job of the next discovery slice.
