# Browser Evidence Report (Part 16)

All screenshots and logs saved under `frontend/e2e-admin-tenant/evidence/e2e03/` (real browser, real backend, real DB).

| Step | Route/Action | API observed | Data shown | Screenshot | Errors/request_id | UI issues | Result |
|---|---|---|---|---|---|---|---|
| 1 | GET /admin/home-services/service-catalog | homeServicesCatalogConsoleApi.listServices | Real service list grouped by category | route_admin_home-services_service-catalog.png | none | none | PASS |
| 2 | GET /admin/home-services/pricing-rules | homeServicesCatalogConsoleApi.listServices + catalogApi.listPricingRules | 9 real pricing rule rows | route_admin_home-services_pricing-rules.png | none | none | PASS |
| 3 | GET /admin/home-services/price-experience | autoPriceOptionsApi.getConfig | Config hero (Auto Price Options / Manual Bargain / Provider-First Matching flags) | route_admin_home-services_price-experience.png | none | none | PASS |
| 4 | GET /admin/home-services/service-areas | catalogApi.listTiers(true) | 3 tier cards (Small/Mid/Large) with linked counts | route_admin_home-services_service-areas.png | none | none | PASS |
| 5 | Click AC Repair row -> General tab | homeServicesCatalogConsoleApi.getServiceDetail | Service name, pricing model, status, description | ac-repair-general.png | none | none | PASS |
| 6 | Click Types tab | (already-fetched detail) | Split AC + Window AC rows in table | ac-repair-types.png | none | none | PASS |
| 7 | Click Brands tab | (already-fetched detail) | LG/Samsung/Voltas brand cards + type-scoping explanation text | ac-repair-brands.png | none | none | PASS |
| 8 | Click Questions/Issues tab | masterDataApi.listIssueTypes | Issue list including Not Cooling / cooling-related | ac-repair-issues.png | none | none | PASS |
| 9 | Click Edit on first pricing rule row | (client-side, uses already-fetched rule) | Modal pre-filled with Service/Type/Brand/Min/Max/Fee/Deduction | pricing-rule-edit-modal.png | none | none | PASS (cancelled, no mutation) |
| 10 | Fill baseline (700/850/10%) + Preview | autoPriceOptionsApi.previewPriceExperience | Low/Mid/High tier cards + full breakdown | price-experience-preview.png | none | none | PASS |
| 11 | Forbidden label scan across all 4 routes | (DOM text scan) | Zero forbidden financial/wallet/escrow/bargain labels | (same 4 route screenshots) | none | none | PASS |

DB cross-checks (psql, not screenshot but logged in this session's transcript): `service_pricing_rules` rows for Split AC+LG (600-950) and Window AC+LG (350-500) both confirmed present, active, and unchanged after all browser interaction — direct proof backing Part 5.

Total evidence files: 12 PNG screenshots + 6 log files, all under `frontend/e2e-admin-tenant/evidence/e2e03/`.
