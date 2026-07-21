# Recertification Findings — new bargain_available/standard_price contract

## Frontend changes (this round)

Consumed the new backend contract fully and correctly:
- `matchAndPrice()` now typed with real `bargain_available`/`standard_price`.
- Added the real `offering_type_id` selection step for `ac_repair` (a real
  catalog quirk: 2 type-scoped `ServicePricingRule` rows, no global fallback
  — confirmed by the backend team, not invented; real type IDs used).
- Added the `bargain_available:false` UI branch: shows the real
  `standard_price` verbatim, "Continue with this price" → `confirm-price-choice`
  with `price_tier:"standard"`.

## Live proof, step by step (real curl against the live, fixed backend)

1. Draft created for `ac_repair` with `offering_type_id` set → real.
2. `serviceability-check` → real `serviceable:true`.
3. `price-estimate` → real `₹82` (catalog estimate, unchanged).
4. `match-and-price` → **real, confirmed**: `bargain_available:false`,
   `standard_price:775.0`, `selected_provider_price_options:null` — exactly
   matching the coordinator's description and the real `ServicePricingRule`
   row for the selected type.
5. `confirm-price-choice` `{price_tier:"standard"}` → **real success**:
   `booking_summary.selected_price_tier:"standard"`,
   `customer_offer:775.0`, `bargain_available:false` — all real, all
   server-derived.
6. `confirm` → **real, NEW blocker found**:
   ```json
   {"error_code": "INVALID_SELECTED_PRICE_OPTION",
    "detail": "Selected price option is no longer valid."}
   ```

## Root cause of step 6 (precise, code-verified)

`mark_ready_for_confirmation()` (`app/engines/home_service_booking/service.py:865-870`)
still has:
```python
selected_tier = (draft.booking_summary or {}).get("selected_price_tier")
if selected_tier not in ("low", "mid", "high"):
    raise ServiceOSException("INVALID_SELECTED_PRICE_OPTION", ...)
```
This check was **not updated** as part of the `bargain_available`/
`standard_price` fix — it still only accepts `"low"/"mid"/"high"`, rejecting
the new, real `"standard"` value that `confirm_price_choice()` now legitimately
accepts and stores. This is a precise, narrow, one-line backend omission
(`"standard"` needs adding to this tuple), not a frontend defect and not a
missing config/data row — a materially different and much narrower blocker
than any found in Rounds 4-6.

## What this means for status

The frontend now correctly and fully implements the new contract end-to-end
up to this exact backend line. `ac_repair` booking submission is still not
completable, but the blocker has moved from "missing BargainRule config"
(Round 4-6) to "one unclosed code path in the just-deployed fix" — reported
here with the exact file, line, and fix needed for the backend team's next
pass.
