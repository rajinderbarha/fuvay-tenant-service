# Admin Catalog/Pricing Route Report (ADMIN-TENANT-E2E-03, Part 1)

Real routes verified in browser via Playwright + real Chrome (admin login `admin@serviceos.in`):

| Route | Page file | Sidebar group | API modules | Result |
|---|---|---|---|---|
| /admin/home-services/service-catalog | app/admin/home-services/service-catalog/page.tsx | Home Services | homeServicesCatalogConsoleApi, masterDataApi | OK, 200, sidebar `hs-service-catalog` active, breadcrumb "Admin > Home Services > Service Catalog", real data (AC Repair etc.), loading skeleton present, no crash, no NaN/undefined |
| /admin/home-services/pricing-rules | app/admin/home-services/pricing-rules/page.tsx | Home Services | homeServicesCatalogConsoleApi, catalogApi, masterDataApi | OK, 200, active nav `hs-pricing-rules`, breadcrumb present, real pricing-rule table rows rendered (9 rows), no NaN/undefined |
| /admin/home-services/price-experience | app/admin/home-services/price-experience/page.tsx | Home Services | autoPriceOptionsApi | OK, 200, active nav `hs-price-experience`, title "Customer Price Experience", real config fetch + preview calculation call, no NaN/undefined |
| /admin/home-services/service-areas | app/admin/home-services/service-areas/page.tsx | Home Services | catalogApi | OK, 200, active nav `hs-service-areas`, title "Service Areas / Zones", real tier cards rendered from `catalogApi.listTiers`, no NaN/undefined |

Evidence: `frontend/e2e-admin-tenant/evidence/e2e03/route_admin_home-services_*.png`, `route-smoke.log`.

Error state: `SectionError` component present on all 4 pages, shows `request_id` with copy button and Retry — verified by reading source (lines in each page's `SectionError`); not force-triggered live since backend was healthy throughout, but confirmed no raw JSON/debug UI in the design.

No route failed. No crash. All 4 target routes plus the 2 optional (overview, completed-job-deduction) exist on disk per the E2E-02 route map and were not separately re-verified beyond their prior E2E-02 smoke pass (out of strict scope, optional).

Result: PASS.
