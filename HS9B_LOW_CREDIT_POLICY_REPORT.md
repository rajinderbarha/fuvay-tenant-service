# HS9B — Low-Credit Policy Report

## Discovery: the core policy already existed from HS4B, unused in this context

`app/engines/provider_portal/router.py::_evaluate_provider_bookability`
(built in HS4B, unchanged structurally) already required
`credit_balance > 0` as one of the hard criteria for `is_bookable`,
with a real blocker reason `USAGE_CREDITS_INSUFFICIENT` when it fails.
This was never disconnected — HS6B's matching engine reads this exact
`is_bookable` flag as its canonical bookability source. **The hard
gate ("a tenant with insufficient usage credits must not keep receiving
future matched jobs") was therefore already functionally enforced**
before this pass — just not documented or tested in the HS9/HS9B
context, and surfaced only as the generic `NOT_BOOKABLE_CANONICAL_STATUS`
reason rather than a credit-specific one.

## What this pass added
A more specific, diagnosable reason code at the matching layer.
`_passes_full_eligibility_gate` (`matching_engine.py`) now inspects the
real `provider_visibility_statuses.bookability_blockers` JSONB array
and returns `INSUFFICIENT_USAGE_CREDITS` specifically when that's the
actual root cause, instead of the generic `NOT_BOOKABLE_CANONICAL_STATUS`
— falls back to the generic code for every other non-bookability cause,
unchanged.

## Live-verified full round trip
1. Set `tenant_billing.credit_balance = 0` for the real dev tenant.
2. `POST /v1/provider/status/refresh` → `is_bookable: false`,
   `bookability_blockers: [{"code": "USAGE_CREDITS_INSUFFICIENT", ...}]`.
3. Direct call to `select_best_provider()` for the exact real
   AC-Repair/Split-AC/LG/Ludhiana-141001 request → `excluded_providers:
   [{"reason_code": "INSUFFICIENT_USAGE_CREDITS"}]`, `signals: None` —
   the tenant is genuinely excluded from matching.
4. Restored `credit_balance = 3979`, re-ran `/status/refresh` →
   `is_bookable: true` — tenant becomes matchable again, confirming the
   restriction is not a one-way lock.

## Credit status classification — not implemented as a distinct field
The ticket's suggested `HEALTHY / LOW_CREDIT / INSUFFICIENT_CREDITS /
SUSPENDED_FOR_CREDITS` enum and configurable
`minimum_required_usage_credits` / `low_credit_threshold` /
`allow_negative_balance` / `block_matching_when_low_credit` settings do
not exist. The real, live-verified behavior today is a simple binary
gate: `credit_balance > 0` blocks matching entirely; there is no
separate "low but still bookable, just warned" middle state — the
tenant-facing `/usage-credits/balance` endpoint does return a
`low_credit: boolean` flag (`< 20` threshold, added in HS9) for UI
display purposes, but this flag does **not** feed into the matching
decision — only the binary `credit_balance > 0` check does.

## Verdict
Low-credit matching restriction: **real and live-verified — a tenant
genuinely cannot receive new matched bookings once usage credits are
exhausted, and genuinely can again once restored.** The richer
multi-tier status/threshold configuration from the ticket's suggested
model is not implemented; the simpler binary policy that already
existed (HS4B) is confirmed working and now has a more specific
diagnostic reason code. Not `NOT_READY_HS9_LOW_CREDIT_POLICY_FAILED` —
the hard gate itself ("must not keep receiving future matched jobs") is
satisfied.
