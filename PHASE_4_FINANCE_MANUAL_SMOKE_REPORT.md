# Phase 4 — Manual Browser Smoke Report

## Environment limitation (same as every prior sprint this session)

No interactive browser automation tool is available in this environment
(confirmed via tool search — only `WebFetch` exists, no JS execution/console
capture/screenshots). Per the established, accepted precedent from prior
sprints this session, the 42-step manual smoke script was executed as an
evidence-based substitute: every step verified via real HTTP requests (SSR
page loads + live API calls with a real super_admin JWT, plus a real
non-privileged JWT for the 403 checks) against the real running backend +
real Postgres + real frontend dev server — not simulated.

## Step-by-step

| # | Step | Verified how | Status |
|---|---|---|---|
| 1-3 | Start backend/frontend, login as Super Admin | Both running; real login succeeded | ✅ |
| 4-6 | Finance menu exists, no forbidden labels | `AdminLayout.tsx` inspected — "Finance" group with Packages/Wallets/Deposits/Top-ups/Claims/Payouts; zero forbidden terms | ✅ source-level |
| 7-8 | Packages page, Starter Home Services exists | `curl /admin/packages` → 200; `GET /v1/admin/packages` → 1 real row, `slug=starter_home_services` | ✅ |
| 9-13 | Package detail: 1000 credits, deposit required, approval flags | `GET /v1/admin/packages/{id}` → `included_credit_amount:1000, security_deposit_amount:5000`; activation semantics confirmed via `TenantPackageAssignment` lifecycle (see backend report) | ✅ |
| 14-15 | Limits/features: staff=5, service area=5 | `GET /v1/admin/packages/{id}/limits` → both rows present (created this sprint to close a real gap) | ✅ |
| 16-17 | Usage Credits: Demo AC Services balance = 0 before approval | `GET .../credit-wallet` → `404 CREDIT_WALLET_NOT_FOUND` (no wallet row = 0, lazily created) | ✅ |
| 18-19 | Ledger: no activation credit before approval | `GET .../credit-ledger` → `{"items":[],"total":0}` prior to test top-up | ✅ |
| 20-22 | Top-up 100, balance becomes 100, ledger entry created | Live-executed: `POST .../top-up {"amount":100,...}` → `balance:100.0`; ledger shows 1 real credit entry | ✅ |
| 23-25 | Debit adjust 100 to revert, balance back to 0, ledger entry created | Live-executed: `POST .../adjust {"entry_type":"debit","amount":100,...}` → `balance:0.0`; 2nd ledger entry confirmed | ✅ |
| 26-27 | Debit that would go negative rejected, request_id shown | Live-executed: `amount:50` against 0 balance → **found and fixed a real 500-crash bug this sprint** (₹ symbol in error message crashing Windows console logging) — now correctly returns `402` with real `request_id` | ✅ (bug found + fixed) |
| 28-29 | Completed Job Deduction: AC Repair = 21 credits, trigger=job_completed | `GET /v1/admin/pricing-rules` → `completed_job_deduction_credits:21`; `GET /v1/admin/settings` → `job_credit_deduction_trigger:"job_completed"` | ✅ |
| 30-31 | Security Deposits: Demo AC Services pending/required | `GET .../security-deposit` → `status:"unpaid", required_amount:5000.0` | ✅ |
| 32-33 | Deposit detail separate from usage credits | Confirmed structurally — separate tables/models/endpoints/pages | ✅ |
| 34-35 | Mark received/hold/release only on safe test record, reason required | Not executed live this pass (the existing deposit is the shared Demo AC Services fixture, not a disposable test record — mutating its status was judged unsafe/unnecessary since the underlying mark-paid/refund/forfeit code paths and their audit-label fix were already verified at the source + via the collision-fix live retest in the backend report) | ⚠️ not re-run live, code-path verified |
| 36-37 | Finance Settings: all 4 baseline values correct | `GET /v1/admin/settings` → all 4 confirmed exact values | ✅ |
| 38-39 | Audit Logs: package/credit/deposit actions recorded | `GET /v1/admin/packages/audit-logs?tenant_id=...` → real entries for `credit_topup`/`credit_adjustment` with real `request_id` on each | ✅ |
| 40 | No browser console errors | **Not verifiable** — no real browser session available (permanent environment constraint) | ⚠️ proxy only |
| 41 | No NaN/null/undefined | Live API numeric fields all proper typed values, never `null` in happy paths; frontend money-formatting helpers (established from Phase 3C) reused across finance pages | ⚠️ strong proxy, not visual |
| 42 | No forbidden labels | Zero matches, `PHASE_4_FORBIDDEN_LABEL_SCAN_REPORT.md` | ✅ |

## Bottom line

38 of 42 steps have strong evidence (live API-level or source-level, several
newly exercised this sprint for genuinely new functionality — including
finding and fixing a real 500-crash bug during step 26-27's execution).
Steps 34-35/40/41 rely on code-path verification or proxy checks rather than
a fresh interactive browser session or disposable test-record mutation;
this mirrors the same accepted limitation from every prior sprint this
session.

## Result: **Evidence-based substitute PASS**, with one real bug found and fixed live during execution (the ₹-crash on negative-balance debit).
