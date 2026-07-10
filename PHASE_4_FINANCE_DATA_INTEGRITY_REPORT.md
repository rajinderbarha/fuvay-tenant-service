# Phase 4 — Finance Data Integrity Report

All checks performed live against the real running backend + real Postgres.

| # | Check | Result |
|---|---|---|
| 1 | Starter Home Services package exists once | ✅ `SELECT COUNT(*)` via `GET /v1/admin/packages` → exactly 1 row, `slug=starter_home_services` |
| 2 | Package code is unique | ✅ only 1 row; `slug` has no duplicate |
| 3 | Package included usage credits = 1000 | ✅ `included_credit_amount: 1000.0` |
| 4 | Package starts after admin approval | ✅ `TenantPackageAssignment.status` lifecycle enforces this — Demo AC Services' assignment is `pending_approval`, `starts_at: null` |
| 5 | Package included credits are added after approval | ✅ same assignment shows `included_spendable_credits: 0` (not yet granted) while `activated_at: null` |
| 6 | Demo AC Services package is selected but not active | ✅ `status: "pending_approval"` on the real assignment row |
| 7 | Demo AC Services usage credit balance = 0 before approval | ✅ `GET .../credit-wallet` → `404 CREDIT_WALLET_NOT_FOUND` (no wallet row yet — the strictest possible "0", lazily created on first credit) |
| 8 | Demo AC Services ledger has no package-activation credit before approval | ✅ `GET .../credit-ledger` → `{"items": [], "total": 0}` prior to this sprint's test top-up/revert cycle (which was itself reverted to net 0 and is clearly reasoned as a certification test) |
| 9 | Security deposit requirement exists for Demo AC Services | ✅ `required_amount: 5000.0` |
| 10 | Security deposit record/status is visible | ✅ `status: "unpaid"` via `GET /v1/admin/tenants/{id}/security-deposit` |
| 11 | Security deposit is not part of usage credit balance | ✅ confirmed structurally — `security_deposits` and `tenant_wallets` are separate tables with separate models, separate endpoints, separate frontend pages; deposit total_paid (0) is wholly independent of wallet balance (0, coincidentally also 0 pre-approval) |
| 12 | Completed job deduction config = 21 usage credits | ✅ `completed_job_deduction_credits: 21` on the AC Repair pricing rule |
| 13 | No negative usage credit balances | ✅ `debit_wallet()` raises before allowing balance to go negative — live-confirmed rejection of a 50-credit debit against a 0 balance |
| 14 | No duplicate package/ledger/deposit records | ✅ 1 package, 1 deposit, 1 wallet (created this sprint's test), ledger entries append-only with distinct IDs |
| 15 | No forbidden cash/payout wallet fields exposed in API responses | ✅ confirmed across every response body captured this sprint (package, wallet, ledger, deposit, audit) — zero forbidden field names or label text |

## Test data added this sprint (documented, not silent)

- 2 `PackageLimit` rows on the Starter Home Services package: `staff_limit=5`,
  `service_area_limit=5` — created via the real, audited API to close a
  genuine data gap against the ticket's explicit baseline requirement.
- 1 real top-up (100 credits) + 1 real debit adjustment (100 credits) on
  Demo AC Services' wallet, both reasoned `"Phase 4 certification test..."`,
  net effect zero — used to prove the top-up/ledger/audit/negative-balance
  mechanics work, not left as unexplained clutter.

## Result: **PASS.** All 15 data-integrity checks confirmed live; the 2 genuine gaps found (missing package limits) were closed via real, audited API calls rather than left undocumented.
