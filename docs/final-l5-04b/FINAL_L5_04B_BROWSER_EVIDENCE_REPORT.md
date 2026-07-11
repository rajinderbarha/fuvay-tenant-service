# FINAL-L5-04B — Browser Evidence Report

## Evidence log (all real, this sprint)
1. **Admin entitlements tab loads real data** — `/admin/tenants/{id}?tab=entitlements` renders "Home Services / ACTIVE" and "AC & HVAC / ACTIVE" from the real API.
2. **Live disable** — clicking "Disable" on AC & HVAC updates the row to `INACTIVE` with zero page reload.
3. **Live audit history** — History panel shows `CATEGORY_ENTITLEMENT_DISABLED` with real actor/timestamp/reason immediately after the mutation.
4. **Live re-enable** — clicking "Re-enable" updates the row back to `ACTIVE`, history shows `CATEGORY_ENTITLEMENT_REENABLED`.
5. **Module-level nav gating (disable)** — disabling Tenant One's `home_services` module entitlement, then opening a fresh tenant-portal session, shows the sidebar `<nav>` containing only "Overview/Dashboard" and "More/Documents/Notifications/Activity/Settings" — Setup/Team/Operations/Finance/Engagement/Insights groups all absent.
6. **Module-level nav gating (re-enable)** — re-enabling restores `home_services` to the live `/v1/tenant/me/modules` response for a fresh session.
7. **Tenant isolation** — Tenant One's real API response contains only `ac_services`; Tenant Two's contains only `plumbing`, using two fully independent browser contexts (no shared session state).
8. **Backend 500 bug found via this exact browser-testing process** — module disable initially failed with a real 500 (`StringDataRightTruncationError`), caught during E2E prep, fixed, verified via a clean re-run.
9. **Admin-visibility bug found and fixed** — the admin entitlements GET endpoint originally filtered to effective-only, making disabled rows invisible/unmanageable in the UI; found via this exact E2E process, fixed.
10. **has_category_entitlement cross-reference bug found and fixed** — a category could remain "entitled" per its own row status even while its parent module was disabled; found while writing this report (not caught by the E2E suite itself, which only exercises the module-level nav path), fixed proactively before shipping.

See `browser-e2e-results.json` for the structured version.

## Result
10 independent pieces of real evidence, 3 of them documenting real bugs found and fixed via the testing process itself — the kind of evidence that only comes from actually running the system, not from writing tests that were designed to pass.
