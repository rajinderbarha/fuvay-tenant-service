# HS6B — Matching Diagnostics Update Report (updated, second pass)

## Status: implemented this pass

### Backend (`matching_engine.py`)
`_passes_full_eligibility_gate` now returns `tuple[bool, str | None]` —
a specific reason code per exclusion, not just a boolean. Codes:
`NOT_BOOKABLE_CANONICAL_STATUS`, `ZIPCODE_NOT_COVERED`,
`SERVICE_NOT_COVERED_IN_AREA`, `TYPE_NOT_COVERED_IN_AREA`,
`BRAND_NOT_COVERED_IN_AREA`, `BLOCKED_BY_BREAK`, `BLOCKED_BY_HOLIDAY`,
`OUTSIDE_BOOKING_WINDOW`, `NOT_AVAILABLE_AT_REQUESTED_TIME`,
`NO_VALID_PRICE_RULE`.

`select_best_provider` gained `requested_at: str | None = None` and now
returns `"excluded_providers": [{"provider_name": str, "reason_code":
str | None}, ...]` alongside the existing counts.

### Backend (`auto_price_options_router.py`)
The diagnostics endpoint extracts `requested_at` from the request body,
passes it through to `select_best_provider`, and returns 5 new response
keys: `excluded_providers` (pass-through of the match result),
`bookability_source: "canonical_provider_status"`,
`area_coverage_source: "normalized_service_area_coverage"`,
`availability_source: "tenant_availability_rules"`,
`pricing_source: "tenant_type_brand_pricing"`.

### Frontend (`lib/api.ts` + `matching-diagnostics/page.tsx`)
`MatchingDiagnosticsResult` interface extended with the 5 new fields.
The diagnostics page renders two new panels directly under the existing
stat cards:
- **"Canonical Sources"** — the 4 source labels, so an admin can see at
  a glance which data model this run's decision came from.
- **"Excluded Providers"** — one row per excluded candidate, provider
  name + a danger badge showing its `reason_code` (or `UNKNOWN`).

## Verdict
Diagnostics update: **implemented**. Reason-code vocabulary is now
actually populated per-candidate and surfaced end-to-end — engine →
router → API type → UI. Verified by 13/13 tests in
`test_hs6b_matching_alignment_completion.py`, including UI-source
inspection asserting both panels' presence and correct field wiring.
Not covered by a live browser/curl session (static + direct-DB-function
verification only — see HTTP E2E report).
