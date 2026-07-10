# HS9B — Matching Restriction Report

(Companion to `HS9B_LOW_CREDIT_POLICY_REPORT.md` — this report focuses
specifically on the matching-engine-side change.)

## Change made
`app/engines/home_service_booking/matching_engine.py::_passes_full_eligibility_gate`
— step 1 (canonical bookability check) now also selects
`bookability_blockers` from `provider_visibility_statuses` and, when
`is_bookable` is false specifically because of
`USAGE_CREDITS_INSUFFICIENT`, returns the more specific
`INSUFFICIENT_USAGE_CREDITS` reason code instead of the generic
`NOT_BOOKABLE_CANONICAL_STATUS`. `ELIGIBILITY_GATE_CODES` updated to
include the new code.

## Why this matters for admin diagnostics
HS6B's admin diagnostics endpoint
(`/admin/home-services/matching-diagnostics`) already surfaces
`excluded_providers: [{provider_name, reason_code}]` per candidate. With
this change, an admin investigating "why wasn't this tenant matched"
now sees `INSUFFICIENT_USAGE_CREDITS` directly instead of having to
separately check the tenant's bookability endpoint to discover the root
cause was credits specifically (versus e.g. a missing service area or
an expired package).

## Live-verified
Direct call to `select_best_provider()` with the real dev tenant at
`credit_balance = 0` → `excluded_providers: [{"provider_name": "Demo AC
Services", "reason_code": "INSUFFICIENT_USAGE_CREDITS"}]`.

## Verdict
Matching restriction reason code: **real, specific, live-verified.**
