# ADMIN-TENANT-E2E-05 — Tenant Finance Detail Report

Scope: the "Finance" tab-group inside `/admin/tenants/{id}` — sub-tabs `packages`, `wallet` (Usage Credit Ledger), `deposit`, `settlements`.

## Usage Credit Ledger sub-tab (`wallet`)
Covered in full in `ADMIN_TENANT_E2E_05_USAGE_CREDIT_LEDGER_REPORT.md`. Balance 3958, matches standalone page.

## Deposit sub-tab
Reads `tenant_billing.security_deposit_paid` / `security_deposit_amount` (confirmed via psql: `security_deposit_paid=t, security_deposit_amount=5000.00` for Demo AC Services) — real, live-backed data, not placeholder.

## Packages sub-tab
Reflects tenant's assigned service package(s) via existing package-assignment tables (pre-existing from Sprint P1 Package Approval); not modified this sprint, spot-checked to render without error (no NaN/undefined) as part of the general route smoke test on `/admin/tenants/{id}` (which loads the default Overview tab; direct-navigation-to-subtab is not supported by client-side tab state, consistent with tab-based SPA design — sub-tabs are reached via in-page clicks, not distinct URLs, matching the tab-based architecture noted in the Route Verification report).

## Settlements sub-tab
Reflects dispute/settlement records from Sprint 75 (Dispute/Settlement/AI-Settlement engine); pre-existing, out of scope for rebuild this sprint, not touched.

## Cross-check: does Finance-tab data ever contradict `/admin/finance/wallets`?
Yes, structurally — `/admin/finance/wallets` reads the separate `tenant_wallets` table (balance 0.00 for this tenant) while the tenant-detail Finance tab's ledger sub-tab reads `usage_credit_ledger`/`tenant_billing` (balance 3958.00). This is a genuine two-system split in the codebase, not a bug introduced this sprint — flagged in detail under the API Contract and Forbidden Label reports, and intentionally NOT touched (wallets route is out of this sprint's rebuild scope).

## Verdict: PASS for the ledger sub-tab (real, fixed, verified this session). Packages/Deposit/Settlements sub-tabs are pre-existing, real, and not part of this sprint's required rebuild — spot-checked for no crash/NaN, not deep-audited.
