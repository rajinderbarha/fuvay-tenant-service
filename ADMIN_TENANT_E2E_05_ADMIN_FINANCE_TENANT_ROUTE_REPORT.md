# ADMIN-TENANT-E2E-05 — Route Verification Report

## Real routes confirmed
| Route | File | Notes |
|---|---|---|
| `/admin/finance/usage-credits` | `app/admin/finance/usage-credits/page.tsx` | Single page, tenant-ID lookup form + ledger table. No separate `/ledger` sub-route (confirmed real, matches handoff note). |
| `/admin/finance/wallets` | `app/admin/finance/wallets/page.tsx` + `[wallet_id]/page.tsx` | Real, but a **separate balance system** (see Forbidden Label / Mismatch finding below). |
| `/admin/home-services/completed-job-deduction` | `app/admin/home-services/completed-job-deduction/page.tsx` | Real, confirmed config-only view (deduction rules by service, not a transaction log). |
| `/admin/tenants` | `app/admin/tenants/page.tsx` | Real list page, 1043 lines, uses `adminTenantsApi` throughout. |
| `/admin/tenants/[id]` | `app/admin/tenants/[id]/page.tsx` | Real, 3067 lines, 23 internal tabs grouped into 7 tab-groups (Overview/Setup/Operations/Finance/Trust & Quality/Media/Audit). Finance group = `packages`, `wallet` (labeled "Usage Credit Ledger"), `deposit`, `settlements`. No separate `/finance` sub-route — confirmed tab-based as expected. |

## Per-route checks (all 5 routes, via Playwright + manual curl)
- Opens in browser: PASS for all 5 (HTTP status < 400, screenshots captured under `evidence/e2e05/`).
- Shell/sidebar/breadcrumb/title: PASS — `AdminLayout` wraps every page; `/admin/tenants/[id]` has its own breadcrumb + tab bar.
- Real API calls: PASS — confirmed via reading each page's data hooks (`usageCreditsAdminApi.getTenantLedger`, `financeApi.listWallets`, `homeServicesCatalogConsoleApi.listServices` + `catalogApi.listPricingRules`, `adminTenantsApi.list`, `tenantApi.get` + ~20 tab-specific hooks).
- Loading/empty/error states: PASS — each page has explicit loading skeletons and empty-state copy; usage-credits and completed-job-deduction show `request_id` on error.
- No NaN/null/undefined visible in rendered text: PASS (asserted by Playwright `route-smoke` test across all 5 routes).
- No raw JSON/debug UI: PASS.

## Key finding (drives several later sections)
`/admin/finance/wallets` is a **third, independent balance system** (`tenant_wallets` table via `platform_commerce`/`finance_hub`), separate from both `/admin/finance/usage-credits` (authoritative `usage_credit_ledger`/`tenant_billing`, balance 3958.00) and from the tenant-detail "Usage Credit Ledger" tab (previously reading a fourth path, `commerceApi.walletBalance`, also on `tenant_wallets`, balance 0.00 — **fixed this sprint**, see API Contract report). `/admin/finance/wallets` itself was left untouched functionally (label-renamed only) since it is out of this sprint's "rebuild finance engine" exclusion — flagged clearly under Forbidden Label Scan and Mock Data reports.

## Verdict: routes verified, real, functioning. No 404s, no crashes.
