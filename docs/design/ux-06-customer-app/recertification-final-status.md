# Recertification Final Status

## Status: `CUSTOMER_APP_SOURCE_COMPLETE_BACKEND_INTEGRATION_BLOCKED` (unchanged token, narrower blocker)

Per the user's own completion bar: promote to `CUSTOMER_APP_DESIGN_COMPLETE`
only if all production routes/runtime tests/live booking evidence genuinely
pass. They do not — real booking submission for `ac_repair` still fails,
now for a different, much narrower, precisely diagnosed reason.

## Required sequence — itemized, real

```
ac_repair discovery          -> REAL (real category/offering picker, live catalog)
→ serviceability              -> REAL (serviceable:true, live)
→ authoritative normal price  -> REAL (₹775, live, source: ServicePricingRule via the new fix)
→ bargain unavailable         -> REAL (bargain_available:false, live)
→ continue at standard price -> REAL (confirm-price-choice price_tier:"standard" succeeds, live)
→ booking review              -> REAL (renders with real price + confirm control)
→ real booking submission     -> BLOCKED (real 422 INVALID_SELECTED_PRICE_OPTION)
→ booking reference           -> NOT REACHED
→ bookings list               -> NOT REACHED (for this specific offering; ac_installation's booking from Round 6 remains real and visible)
→ booking detail              -> NOT REACHED (for this specific offering)
→ refresh persistence         -> NOT REACHED (for this specific offering)
```

7 of 11 steps genuinely proven live through the actual production app UI
(screenshots: `recert-01` through `recert-05`). The blocker is not a
frontend defect: `mark_ready_for_confirmation()`
(`app/engines/home_service_booking/service.py:865-870`) still validates
`selected_price_tier` against only `("low", "mid", "high")`, rejecting the
new, real `"standard"` value the same fix's `confirm_price_choice()`
legitimately produces. One line needs to change on the backend:

```python
if selected_tier not in ("low", "mid", "high", "standard"):
```

## Frontend-owned work: complete

Every frontend responsibility in this recertification is done and verified:
consuming `bargain_available`/`standard_price`, the real `offering_type_id`
step, the standard-price UI, and calling `confirm-price-choice` with the
correct real `"standard"` value — all confirmed working via live curl AND
live Playwright through actual production navigation. The remaining failure
is 100% attributable to one unclosed backend code path, precisely located.

## Test/typecheck evidence

- `tsc --noEmit`: 0 errors (verified after this round's changes).
- `jest --runInBand`/`jest`: 48/48 passing across 4 runs (1 clean-install +
  3 consecutive, including one default-parallel-workers run) — zero
  flakiness.

## Why not CUSTOMER_APP_DESIGN_COMPLETE

The user's own bar requires "all production routes/runtime tests/live
booking evidence genuinely pass." Booking reference/list/detail/refresh for
`ac_repair` (the one customer-catalog-visible offering) were not reached.
Claiming DESIGN_COMPLETE would misrepresent that. The status remains
`SOURCE_COMPLETE_BACKEND_INTEGRATION_BLOCKED`, now with the tightest,
most precisely-scoped blocker of any round in this phase — a single-line
backend fix away from full completion, with the exact fix already known
and reported.
