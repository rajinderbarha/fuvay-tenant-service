# Home Services Menu + Price Range — Test Results

## TypeScript

`npx tsc --noEmit` in `frontend/super-admin`: **0 errors, exit code 0**
(confirmed twice — immediately after all page/nav edits, and again as a
final check before writing this report).

## Build

`npm run build` for `frontend/super-admin` could not be re-verified as a
fresh production build this sprint — a dev server was already running on
port 3000 from earlier in this session (not started for this ticket), and
`next build` refused to run concurrently ("Another next build process is
already running"). Rather than force-kill a process that might be an
active session the user is using to view the site, TypeScript's own
clean compile (`tsc --noEmit`, 0 errors) is relied on as the hard gate —
consistent with the ticket's explicit rule "If TypeScript fails, return
NOT_READY_TYPESCRIPT_FAILED," which this satisfies. See Remaining
Blockers for the follow-up action (re-run `npm run build` once the dev
server is stopped).

## New certification tests

`pytest tests/test_home_services_menu_and_price_range.py`: **27/27
passed.** Covers: Home Services nav group has all 9 required items,
"Pricing Rules" removed from the common "Pricing & Rules" group (which
now only has genuinely vertical-agnostic items), no Home-Services href
duplicated outside the Home Services group, all 4 new pages exist, old
`/admin/pricing-rules` shows a deprecation banner + forward link while
staying functional, new Pricing Rules page has the exact ticket table
columns/form fields/validation messages and is Home-Services-scoped,
Service Areas/Completed Job Deduction/Settings pages have real content,
tenant wizard still shows Platform Allowed Range and only exposes
tenant-editable inputs, backend still enforces min/max bounds, the
symmetric Low/Mid/High formula matches this ticket's own example exactly
(800–1000 @ 10% → 880/990/1100), Low never equals the raw provider min,
brand override still respects `can_override_price`, publish still blocks
on incomplete pricing, Home Services scope guard message intact, 0
forbidden labels across all 4 new pages.

## Live evidence-based smoke test

```
GET  /v1/admin/pricing-rules?page_size=5                                     → 200 (real rules, unaffected by menu changes)
PUT  /v1/tenant/catalog/enabled-services/{id}/types/{Window AC}/pricing
     {tenant_min_price:100, tenant_max_price:200}                            → 422 TENANT_PRICE_BELOW_ADMIN_MIN, request_id present
PUT  /v1/tenant/catalog/enabled-services/{id}/types/{Window AC}/pricing
     {tenant_min_price:600, tenant_max_price:9999}                            → 422 TENANT_PRICE_ABOVE_ADMIN_MAX, request_id present
```

## Regression check

`pytest tests/test_home_services_menu_and_price_range.py
tests/test_admin_home_services_catalog_setup.py
tests/test_tenant_home_services_service_setup_wizard.py`: **98/98
passed** — 0 regressions from the menu reorganization or the 4 new admin
pages.

## Backend

No backend code was changed for this ticket (Part B's backend enforcement
was already built and re-verified live, unchanged). No new pytest files
needed on the backend side beyond the shared `test_home_services_menu_and_price_range.py`
static-inspection file (which does import and directly call the real
`compute_symmetric_customer_price_tiers` function to verify the formula,
not just inspect source text).
