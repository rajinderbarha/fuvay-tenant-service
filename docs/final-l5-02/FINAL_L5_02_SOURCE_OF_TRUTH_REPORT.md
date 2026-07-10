# FINAL-L5-02 — Source-of-Truth Certification

Verified against the live code + canonical DB, not assumption.

| Domain | Canonical source | Verified | Legacy/dormant |
|---|---|---|---|
| Usage Credit Balance | `tenant_billing.credit_balance` | **Confirmed** — read by `home_service_booking/matching_engine.py`, `provider_portal/router.py`, `tenant_engine/admin_service.py` (the active bookability + admin paths). Canonical seed writes only here. | `tenant_wallets.credit_balance` — NOT read by matching/bookability |
| Usage Credit history | `usage_credit_ledger` | **Confirmed** — the exactly-once deduction row lives here; arithmetic `4000 + (-21) = 3979` verified | — |
| Home Services jobs | `service_jobs` | **Confirmed** — canonical seed's 5 jobs; real admin/tenant/staff/customer endpoints back onto it (see jobs source-of-truth inventory from FINAL-L5-01B) | `jobs` (field_ops) — legacy Field Ops table, separate |
| Tenant credit source in matching | `tenant_billing` via `is_bookable` gate | **Confirmed** — the matching engine's HS6B eligibility gate reads ONLY `provider_visibility_statuses.is_bookable` (which derives from `tenant_billing`). A code comment documents that a *removed* bug previously re-derived readiness from `tenant_wallets/security_deposits` — that parallel path was deleted. | `tenant_wallets` in matching: **removed** (documented in code) |

## Critical rule compliance
- **"Do not treat dormant tenant_wallets as the active credit source"**: PASS — `tenant_wallets` is only wrapped by a legacy `ProviderCreditWalletService` (Sprint 23) and referenced in dashboard/marketing/analytics *reporting* services, never in the active bookability/deduction path.
- **"Use tenant_billing.credit_balance and usage_credit_ledger"**: PASS — confirmed as the active read/write sources.
- **"Use service_jobs as the canonical Home Services jobs source"**: PASS.

## Result
**Source-of-truth certification: PASS.** No active endpoint uses dormant legacy sources for the credit/jobs critical paths. The one live code reference to `tenant_wallets` in the matching engine is a comment recording that the legacy path was *removed*.
