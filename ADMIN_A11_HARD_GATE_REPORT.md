# Admin Sprint A11 — Hard Gate Report

All 10 hard gates checked live against the running backend + both frontends.

| # | Gate | Result | Evidence |
|---|---|---|---|
| 1 | TypeScript fails | **PASS** | `tsc --noEmit` — 0 errors in both `frontend/super-admin` and `frontend/tenant-portal` |
| 2 | Home Services pages appear in common/global menu | **PASS** | `test_pricing_rules_removed_from_common_pricing_group`, `test_no_home_services_item_duplicated_in_another_group` — 2/2 passing; "Pricing & Rules" group now contains only Pricing Tiers/City-Zip Mapping/Provider Pricing Overrides, all 9 Home-Services items live only in the "Home Services" group |
| 3 | Tenant price can go below admin minimum | **PASS (blocked)** | Live: `PUT .../types/{id}/pricing {min:1,max:2}` (admin floor ₹550) → `422 HTTP` (rejected) |
| 4 | Customer Low/High do not include platform fee | **PASS (fee included)** | Live: Selected Range ₹350–₹420 @ 10% → `customer_high_price=462.0 != 420.0` (pre-fee value) |
| 5 | Manual bargain setup appears as active module | **PASS** | `GET /v1/admin/home-services/config` → `manual_bargain_rules_enabled: false`; no "Bargain Rules" nav item; old bargain-rules page marked `[Deprecated]` |
| 6 | Wallet/withdraw/payout labels appear | **PASS** | Forbidden-label grep returned 0 matches across every Home Services page built/touched this session (Service Catalog Console, Pricing Rules, Service Areas/Zones, Completed Job Deduction, Settings, Customer Price Experience, Tenant Setup Wizard) |
| 7 | request_id missing from errors | **PASS** | Every `ServiceOSException` flows through the platform-wide RFC 7807 handler, which always includes `request_id`; live-verified on every 422 raised during this session's testing (`TENANT_PRICE_BELOW_ADMIN_MIN`, `SELECTED_RANGE_BELOW_ADMIN_MIN`, etc.) |
| 8 | Mock runtime data is used | **PASS** | Every page built this session calls real backend endpoints against the live Postgres database — no mock/hardcoded runtime data (see individual sprint API Mapping reports) |
| 9 | Admin actions bypass permissions | **PASS** | All new/modified endpoints gated by `require_permission(P.CATALOG_PRICING_READ/WRITE)`, `require_permission(P.TENANT_UPDATE)`, or `require_permission(P.PRICING_BARGAIN_EVALUATE_PREVIEW)` — confirmed via static test + live use of a real authenticated admin/tenant token throughout |
| 10 | Non-Home Services are affected by Home Services flow | **PASS** | `GET /v1/tenant/catalog/home-services/available-services` hard-scoped to the real Home Services category — live-verified returns 15 items out of 57 total active services across all 14 verticals; `get_home_services_category_id()` raises `HOME_SERVICES_CATEGORY_NOT_FOUND` rather than ever falling back to another vertical's data |

## Result: 10/10 hard gates PASS
