# HS6 — Test Results

## New test file
`tests/test_hs6_provider_matching_price_fix.py` — **9/9 passing**.
Covers both real bugs found this sprint (fee-inclusive price formula,
type/brand-scoped bargain-rule resolution) plus regression guards
(provider-first ordering, Home Services scope).

## Regression
```
pytest tests/test_provider_first_matching_and_price_choice.py tests/test_customer_price_experience_calculation_fix.py tests/test_deactivate_manual_bargain_auto_price_options.py tests/test_home_services_only_bargain_scope.py -q
```
**76/76 passing** (1 pre-existing test updated to reflect the corrected,
fee-inclusive `high_price` — was asserting the buggy pre-fee value).

```
pytest tests/ -k "home_service_booking or matching or bargain or provider_first" -q
```
**206 passed, 0 failed.**

## TypeScript
0 errors, both frontends (no frontend files modified this sprint).

## Live verification
Pure-function level: `compute_price_tiers()` re-tested directly against
the ticket's exact numeric example (700–850 @ 10% → Low 770, High 935)
— matches exactly.

**Not performed**: full HTTP end-to-end live curl through
`POST /{draft_id}/match-and-price` (requires a pre-built booking draft
via the chatbot flow — out of this sprint's remaining time budget).

## Verdict
All new and regression tests passing. TypeScript clean. Function-level
live verification confirms both fixes are numerically correct; full
HTTP end-to-end live verification is the sprint's main documented gap.
