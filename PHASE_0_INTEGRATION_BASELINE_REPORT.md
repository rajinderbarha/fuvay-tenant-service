# Phase 0 — Frontend/Backend Integration Baseline Report

All 11 checks verified by confirming (a) the frontend page calls the exact
backend endpoint, and (b) that endpoint returns the baseline data confirmed
live in `PHASE_0_BACKEND_BASELINE_REPORT.md`. No browser session was used
(see `PHASE_0_MANUAL_SMOKE_REPORT.md`) — this is an API-contract-level
integration check, not a pixel-verified one.

| # | Check | Result |
|---|---|---|
| 1 | Sidebar matches backend effective menu | ✅ `AdminLayout.tsx` calls `verticalCatalogApi.getEffectiveMenu()` → `GET /v1/admin/catalog/navigation/effective-menu`, confirmed live 200 |
| 2 | Platform Settings UI shows correct backend values | ✅ `/admin/settings` calls the same `GET /v1/admin/settings?tier=platform` endpoint verified in the backend report |
| 3 | Engine Management UI shows required engines | ✅ `/admin/engines` calls `GET /v1/admin/engines/summary` and `/health`, both confirmed live (39 engines, 0 degraded) |
| 4 | Vertical page shows Home Services enabled | ✅ `/admin/verticals` calls `GET /v1/admin/verticals`, confirmed `home_services.is_enabled=true` |
| 5 | Catalog UI shows AC Repair data | ✅ `/admin/master-services` calls `GET /v1/admin/master-services`, AC Repair confirmed present |
| 6 | Types & Brands UI shows Split AC + LG mapping | ✅ `/admin/types-brands` calls `GET /v1/admin/catalog/type-mappings` + `/brand-mappings`, both confirmed to return Split AC and LG for AC Repair |
| 7 | Issue Types UI shows Not Cooling | ✅ `/admin/service-setup/issue-types` calls `serviceOptionApi`, backed by `GET /v1/admin/master-services/{id}/issues`, confirmed `AC Not Cooling` present and `customer_visible=true` |
| 8 | Service Options UI shows Gas Refill | ✅ `/admin/service-setup/service-options` backed by `GET /v1/admin/master-services/{id}/options`, confirmed `Gas Refill` present |
| 9 | Pricing Rules UI shows ₹800 AC Repair rule | ✅ `/admin/pricing-rules` calls `GET /v1/admin/pricing-rules`, confirmed `base_price=800` row present |
| 10 | Packages UI shows Starter Home Services | ✅ `/admin/packages` calls `GET /v1/admin/packages`, confirmed `Starter Home Services` present with 1000 credits |
| 11 | Tenant UI shows Demo AC Services not bookable | ✅ `/admin/tenants` calls `GET /v1/admin/tenants`, confirmed `Demo AC Services` with `verification_status=pending` |

**11/11 integration checks pass at the API-contract level.**
