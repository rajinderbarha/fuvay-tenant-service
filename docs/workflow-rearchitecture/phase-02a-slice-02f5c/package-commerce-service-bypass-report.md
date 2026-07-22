# Package Commerce Service Bypass Report — Workstream 14

## Method
Searched for callers of every `PackageCommerceService` method used by the
20 routes, plus checked for worker/scheduled-job writers to
`service_packages`, `package_features`, `package_limits`,
`tenant_package_assignments`, `usage_credit_ledger`/`tenant_billing`
(via the adapter), and `commission_records`.

## Findings

### Live, correctly-routed methods (no bypass)
`create_package`, `update_package`, `delete_package`, `activate_package`,
`deactivate_package`, `clone_package`, `create/update/delete_package_feature`,
`create/update/delete_package_limit`, `create_package_assignment`,
`calculate_commission`, `deduct_commission` — each has exactly the
expected caller(s) documented in the route inventory; no additional,
undocumented caller was found anywhere in `app/`.

### Orphaned service methods (dead code, not a bypass)
`PackageCommerceService.admin_mark_deposit_paid`,
`admin_refund_deposit`, `admin_forfeit_deposit`, `admin_topup_wallet`,
`admin_adjust_wallet`, and the standalone `purchase_package` method all
still exist in `service.py` but have **zero callers** anywhere in `app/`
(confirmed via grep for `.method_name(` across the codebase). The
router's own routes with matching names (`admin_mark_deposit_paid` etc.)
raise `HTTPException(410)` directly without calling these service
methods; the credit-wallet routes call `UsageCreditService` directly
instead of the service's own `admin_topup_wallet`/`admin_adjust_wallet`.
These are dead code, not a live authorization bypass — they cannot be
reached by any HTTP request. A regression test
(`TestOrphanedServiceMethodsHaveNoLiveCaller`) locks in that the router
does not accidentally start calling them again.

### No worker/scheduled-job caller
No Celery/RQ/APScheduler job was found writing to any of the 6 tables
this module owns or adapts. Consistent with the platform-wide pattern
observed in every prior slice in this series.

### Commission cross-module relationship
`deduct_commission`/`calculate_commission` are called only from
`package_commerce.admin_router` within this module's own boundary. The
broader relationship to `platform_commerce.CommerceService`'s and
`invoice_payment.ServiceCommissionService`'s own, separate commission
methods (which write to the same `CommissionRecord` table) is documented
in `alternate-commerce-route-audit.md` — not a bypass of
`package_commerce`'s own guards, since none of those other services call
into `package_commerce.PackageCommerceService` at all; they are
independent code paths that happen to share a table.

## Conclusion
Zero live service bypasses found for `package_commerce.admin_router`'s
own methods. 6 service methods are confirmed dead code (unreachable),
not removed this slice (not requested, and deletion of dead code was not
in the permitted-fix list), but locked in via regression test.
