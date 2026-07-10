# Admin Route Browser Smoke Report (Part 6)

Real Chrome (channel: 'chrome') via Playwright, logged in as `admin@serviceos.in`. 13 routes
covering every rendered sidebar group (Overview, Providers, Operations, Catalog, Pricing & Rules,
Home Services, Finance, Marketing & Growth, Platform):

```
/admin/dashboard | status=200 | len=4336 | hasSidebar=1 | hasHeader=1
/admin/tenants | status=200 | len=2546 | hasSidebar=1 | hasHeader=1
/admin/bookings | status=200 | len=1207 | hasSidebar=1 | hasHeader=1
/admin/customers | status=200 | len=1162 | hasSidebar=1 | hasHeader=1
/admin/categories | status=200 | len=1472 | hasSidebar=1 | hasHeader=1
/admin/pricing-tiers | status=200 | len=1637 | hasSidebar=1 | hasHeader=1
/admin/home-services/service-catalog | status=200 | len=2517 | hasSidebar=1 | hasHeader=1
/admin/finance | status=200 | len=1703 | hasSidebar=1 | hasHeader=1
/admin/marketing | status=200 | len=2294 | hasSidebar=1 | hasHeader=1
/admin/engines | status=200 | len=3723 | hasSidebar=1 | hasHeader=1
/admin/security | status=200 | len=1440 | hasSidebar=1 | hasHeader=1
/admin/audit-logs | status=200 | len=2842 | hasSidebar=1 | hasHeader=1
/admin/users | status=200 | len=1923 | hasSidebar=1 | hasHeader=1
```
(Raw log: `frontend/e2e-admin-tenant/evidence/e2e02/route-smoke.log`; screenshots:
`frontend/e2e-admin-tenant/evidence/e2e02/smoke_admin_*.png`.)

All 13: status < 400, shell present (sidebar+header both count=1), no "NaN" text, no crash, no
unintended 404. Combined with the 6 nested-route active-state tests (Part 3) and the login/logout/
auth tests (Part 9), 22 of 26 new Playwright tests directly cover route-open/shell/active-state
behavior; all 26 passed (`26 passed (3.9m)`, full run in TEST_RESULTS).

Not deep-content-verified per route (i.e. did not assert exact KPI numbers/table rows) — that is
explicitly out of this sprint's scope (full page functional certification is future
page-by-page work); this sprint certifies shell+nav+no-crash only, per spec.
