# ADMIN-TENANT-E2E-05 — Tenant Credit Status Report

"Credit status" for Demo AC Services, cross-checked across every surface that shows it.

| Surface | Field | Value | Source table |
|---|---|---|---|
| `/admin/finance/usage-credits` | Current Balance | 3958 | `usage_credit_ledger` (via `getTenantLedger`) |
| `/admin/tenants/{id}` → Finance → Usage Credit Ledger | Usage Credit Balance StatCard | 3958 | same endpoint, `usageCreditsAdminApi.getTenantLedger` |
| `/admin/tenants/{id}` → Overview readiness check | "Usage Credits Available" | ok=true (`w?.credit_balance > 0`) | same `wallet` hook |
| `tenant_billing` table (psql) | `credit_balance` | 3958.00 | authoritative |
| `tenant_wallets` table (psql) | `credit_balance` | 0.0000 | separate, legacy/unused-by-Home-Services system |

## Consistency verdict
All three **admin-facing UI surfaces** now agree (3958), after this session's fix to the tenant-detail ledger tab's rendering path (Finance group must be clicked first — a real Playwright-test bug, not a data bug, see Usage Credit Ledger report) and the earlier-sprint fix that pointed the tab's data hook at the correct API.

The `tenant_wallets` row (0.00) is a genuinely separate system read by `/admin/finance/wallets` and by `field_ops`/`platform_commerce` job-closing logic — it is not surfaced anywhere as "the" tenant credit status in the pages in scope for this sprint, so it does not create a user-facing contradiction, but it is a real architectural inconsistency flagged for follow-up (see API Contract report).

## Low-balance alert path
`StatCard ... alert={!!w?.low_balance_alert}` — real conditional wiring present in `app/admin/tenants/[id]/page.tsx`; not exercised in this session's tests (would require driving the balance below the `low_balance_alert` threshold), noted as untested-but-present logic.

## Verdict: PASS — tenant credit status is consistent and accurate everywhere it is shown in-scope; the disconnected `tenant_wallets`/`/admin/finance/wallets` system is a documented pre-existing architecture split, not a defect introduced or missed this sprint.
