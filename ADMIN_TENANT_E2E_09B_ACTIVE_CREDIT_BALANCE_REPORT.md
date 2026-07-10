# ADMIN-TENANT-E2E-09B — Active Credit Balance Report

Confirmed via direct psql:
- `tenant_billing.credit_balance` = **3937.00** for Demo AC Services (`34b427a7-...`).
- `tenant_wallets.credit_balance` = **0.0000** for the same tenant (present in schema, but
  dormant/legacy).

Confirmed via code read (`app/engines/provider_portal/router.py:922-1053`,
`_evaluate_provider_bookability`): the real bookability gate reads
`SELECT credit_balance, security_deposit_paid, security_deposit_amount FROM tenant_billing
WHERE tenant_id=:tid` and treats `credit_balance > 0` as the "usage_credits_available" pass
condition. No reference to `tenant_wallets` anywhere in this function.

Confirmed via code read (`app/engines/home_service_booking/matching_engine.py:391-405`,
inline docstring in `_passes_full_eligibility_gate`): a prior sprint explicitly REMOVED a
second, parallel readiness calculation that used to read `tenant_wallets` alongside other
tables, specifically because it produced inconsistent results vs. the canonical
`is_bookable` flag. `tenant_wallets` is confirmed dormant and explicitly documented as
LEGACY_FALLBACK_ONLY / removed from the live matching gate.

UI check: grepped tenant-portal service-setup/coverage/pricing pages — no reference to
`tenant_wallets` or "wallet" balance display found (see Forbidden Label Rescan).

Publish-readiness: `GET /v1/provider/status` (the real readiness/bookability endpoint) is
backed by the same `_evaluate_provider_bookability` function — confirmed uses `tenant_billing`
exclusively.

Verdict: `tenant_billing` is confirmed as the correct, live-used balance source everywhere it
matters. `tenant_wallets` is correctly dormant and unreferenced by real bookability/matching
logic.
