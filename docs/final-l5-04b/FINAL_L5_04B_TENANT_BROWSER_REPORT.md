# FINAL-L5-04B — Tenant Real Chromium E2E Report

## Test: `FINAL-L5-04B Tenant navigation module-level entitlement gating` — **Passing**

### Tenant One scenario
| Mission step | Result |
|---|---|
| Login | Real login, `owner@demo-ac-services.local`, fresh browser context |
| Verify only Tenant One modules/categories | Verified via real API call from within the browser session (`/v1/tenant/me/modules` → `["home_services"]`) |
| Open entitled category | No category-specific route exists to "open" (honest gap, see Tenant Navigation Integration Report) — entitlement was instead proven at the data/API layer |
| Verify setup routes | Not independently walked through the UI this sprint; the underlying guard (`enable_service` 403/201) was proven via curl (Live API Smoke Report) |
| Verify disabled category disappears | **Verified at module granularity**: disabling the tenant's only module entitlement removed the Operations/Finance sidebar groups, confirmed via the sidebar `<nav>` element's own text content (not whole-page body text, which was found to give a false pass due to CSS `text-transform` affecting Playwright's `innerText` case) |

### Tenant Two scenario
| Mission step | Result |
|---|---|
| Login | Real login, `owner@isolation-test-services.local`, separate fresh browser context |
| Verify different entitlement set | Real API call confirmed `categories: ["plumbing"]`, not `["ac_services"]` |
| Verify Tenant One-only category does not appear | Confirmed — `ac_services` never appears in Tenant Two's response |
| Attempt direct route | No category-specific tenant-portal route exists to attempt directly (same honest gap as Tenant One) |
| Verify denial | N/A for the same reason — proven instead via the isolation guarantee (Tenant Two's own entitlement set never includes Tenant One's category, so any hypothetical category-gated action would correctly be denied by the same `has_category_entitlement()` check proven in Service Setup Enforcement) |

## Result
Both tenants' isolation and module-level gating are real, browser-proven with fresh, independent contexts (not shared session state). The category-specific route-level scenarios from the mission couldn't be executed literally because no such route exists in the tenant portal's current architecture — substituted with the closest real, honest equivalent (data-layer + API-layer proof) rather than fabricated.
