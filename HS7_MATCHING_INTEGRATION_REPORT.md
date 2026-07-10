# HS7 — Matching Integration Report

## Result: integrated and live-verified, following the correct order

The real customer flow calls, in order:
1. `PUT /v1/customer/home-services/booking-drafts/{id}` — service/type/brand/issue/zipcode collected.
2. `POST .../serviceability-check` — real HS5B-canonical coverage check (fixed this pass, see main report).
3. `POST .../match-and-price` — backend selects exactly one provider (HS6/HS6B provider-first matching), then computes its Low/Mid/High price options. The customer never sees or picks from a list.
4. `POST .../confirm-price-choice` — customer submits only a tier name (`"low"|"mid"|"high"`), never a raw amount, never a provider.

This is the ticket's required order (provider selected **before** price
choice) and matches HS6/HS6B's certified `select_best_provider` +
`compute_price_tiers` — reused, not reimplemented.

## Live-verified (real database, real seeded catalog)
`AC Repair + Split AC + LG + 141001` → selected provider "Demo AC
Services" → price options `Low 770 / Mid 850 / High 935` (exactly the
ticket's own worked example: 700–850 range, 10% fee) → customer chose
`mid` → booking created with `selected_price_option: "mid"`,
`selected_price_amount: 850.0`.

## Negative path verified
Manually flipping the selected provider's `provider_visibility_statuses.is_bookable`
to `false` between price-choice and confirmation, then calling `/confirm`,
correctly returned `SELECTED_PROVIDER_NOT_BOOKABLE` (422) — see
`HS7_BOOKING_CREATION_REPORT.md`. Restored afterward.

## Verdict
Matching integration: **working, real, correctly ordered.** Not
`NOT_READY_HS7_MATCHING_INTEGRATION_FAILED` — provider selection
genuinely precedes price choice at both the API-call-order level and the
data level (price options only exist after a provider is matched).
