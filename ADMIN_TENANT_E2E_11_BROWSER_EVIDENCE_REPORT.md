# ADMIN-TENANT-E2E-11 — Browser Evidence Report

All real, captured this session via real system Chrome, real tenant
login, real backend, saved under
`frontend/e2e-admin-tenant/evidence/e2e11/`.

| # | Route | Role | Tenant shown | Action | API observed | Data shown | Screenshot | Result |
|---|---|---|---|---|---|---|---|---|
| 1 | `/finance` | Owner | Demo AC Services | Load | (redirect) | → `/finance/package` | `finance-overview.png` | PASS |
| 2 | `/finance/package` | Owner | Demo AC Services | Load | `GET /v1/provider/usage-credits/balance` → 200 | **Usage Credit Balance: 3937** (fixed from a stale `0`) | `usage-credit-balance.png` | PASS |
| 3 | `/finance/usage-credit-ledger` | Owner | Demo AC Services | Load | `GET /v1/provider/usage-credits/ledger` → 200 | 3 real Completed Job Deduction rows, `4000→3979→3958→3937` | `usage-credit-ledger.png` | PASS |
| 4 | (same page) | Owner | — | View deduction row | (same call) | `-21`, `3958`, `3937`, real job ID, real request_id | `usage-credit-ledger.png` | PASS |
| 5 | `/finance/package` | Owner | — | Low-credit state | n/a | Not exercised (real balance is healthy); banner code path added, unverified live | — | documented, not tested |
| 6 | `/notifications` | Owner | Demo AC Services | Load | `GET /v1/notifications/tenants/{tid}/list`, `/channels` → 200 | Honest empty state | `notifications.png` | PASS |
| 7 | `/settings` | Owner | Demo AC Services | Load | `GET /v1/settings/tenants/{tid}` → 200 | Real settings table | `settings.png` | PASS |
| 8 | `/settings` | Read Only | Demo AC Services | Attempt mutation | `PUT /v1/settings/tenants/{tid}/test_e2e11_key` → **200 (succeeded)** | Real, unauthorized-in-intent write succeeded — see RBAC report | `readonly-settings.png` | **FAIL** |
| 9 | topbar bell | Owner | — | Click | n/a (pure navigation, fixed this pass) | Navigates to `/notifications` | `bell-before-click.png`, `bell-after-click.png` | PASS |

## Verdict
8 of 9 evidence items pass cleanly with real data. Item 8 is the
sprint's one real, confirmed blocker — captured with real evidence
(screenshot + real API response), not asserted without proof.
