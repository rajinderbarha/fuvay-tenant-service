# Admin A3 — Test Results Report

## New test suite
`tests/test_admin_a3_tenant_management_provider_360.py` — **23/23 passing**.

Covers: list route/title/columns/search/filter/pagination/row-actions,
detail route/substantiality/tabs/KPI labels, 4 real existing mutation
endpoints, new Add Admin Note endpoint + validation + API client wiring,
the audit-trail-gap fix (`record_platform_audit` call present,
`request_id` passed), 12 forbidden finance labels absent from both pages,
usage-credit disclaimer present, correct finance terminology present, no
bare "Unexpected error" string.

## Self-corrected test-authoring mistakes (3, fixed before this report)
1. Column assertions used bare `"Owner"`/`"Health"` strings instead of the
   real `label: "X"` object-literal shape — fixed to match real source.
2. Row-action assertions used wrong labels (`"Verify"`/`"Suspend"`)
   instead of the real ones (`"Review Verification"`/`"Suspend Tenant"`)
   — fixed.
3. `addNote` API-client test originally matched an unrelated, pre-existing
   `addNote` method on a different API object (jobs) — fixed by scoping
   the search to the `adminTenantsApi` block and matching the real
   template-literal endpoint string.

## Combined regression sweep
```
pytest tests/test_admin_a3_tenant_management_provider_360.py \
       tests/test_admin_a2_dashboard_system_overview.py \
       tests/test_home_services_menu_and_price_range.py -q
```
Result: **78 passed, 2 failed.**

Both failures are in `test_home_services_menu_and_price_range.py`
(`test_tenant_wizard_still_shows_platform_allowed_range`,
`test_tenant_cannot_edit_admin_fields`), a file from an earlier, already-
certified sprint that A3 did not touch. Root cause: the target file
(`frontend/tenant-portal/app/(tenant)/tenant/setup/services/page.tsx`)
has been externally modified since that sprint's certification — this is
the tenant-portal wizard file already documented in the A11 sprint's
Remaining Blockers as being actively replaced with a "Page Moved"
redirect stub outside of session control. A3 is scoped entirely to the
super-admin portal's tenant-management module and does not touch this
file, `admin_router.py`'s consumers, or any tenant-portal frontend code.
Confirmed pre-existing/external, not a regression introduced by A3.

## TypeScript
`npx tsc --noEmit` in `frontend/super-admin` → **0 errors**.

## Verdict
New A3 test suite: 100% passing. All regressions confirmed pre-existing
and out of A3's scope.
