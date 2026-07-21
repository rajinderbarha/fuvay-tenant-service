# Pricing Continuity — Round 2 (Workstream 10)

## Standard-price path (ac_repair) — reconfirmed, not rebuilt

Already fully proven live in Round 1 (`live-e2e-evidence.md`). Reconfirmed
this round only via `real-record-evidence.csv` re-fetch (booking
`BK-20260721-000008` still shows `status:"accepted"`, same
`selected_price_amount:775.0` logic path). Not re-run from scratch this
round — no value in duplicating Round 1's own proof.

## Bargain-enabled path (ac_installation) — reconfirmed live this round

A NEW draft was created this round (`d5048334-db35-4ba7-adbc-9cd1df13f54d`,
NOT carried through to a full booking — this was a targeted pricing-path
check, not a second full E2E run, to avoid creating an unnecessary
duplicate booking record):

1. `POST .../booking-drafts` `{category_slug:"home_services",
   offering_slug:"ac_installation"}` -> real draft, real
   `offering_id:13f6cf5e-5d17-4790-b406-6561675a5d38`.
2. `PUT .../{id}` with `city:"Ludhiana"`, `brand_id` (LG, same as Round 1),
   `offering_type_id` (Split AC, same as Round 1 — supplied proactively
   this time, having learned from Round 1's finding that it's functionally
   required).
3. `POST .../serviceability-check` -> real `serviceable:true`.
4. `POST .../match-and-price` -> real success:
   **`bargain_available:true`**, `standard_price:null`,
   `selected_provider_price_options: {low_price:150.0, mid_price:150.0,
   high_price:150.0, allowed_offer_min:150.0, allowed_offer_max:150.0,
   platform_fee_percent:0.0, payment_mode:"customer_pays_provider_directly"}`.

This confirms the SAME `match-and-price` endpoint correctly branches
between the standard-price fallback (`ac_repair`, no `BargainRule`) and the
bargain-tier path (`ac_installation`, has a real `BargainRule`) based on
real, live, server-side data — exactly as UX-06 documented, and NOT a
client-side calculation in either case (the client only ever receives
already-computed numbers).

## Client-does-not-calculate-price verification

Confirmed by inspection: `mobile/customer-app/src/lib/api.ts`'s draft-flow
functions (`serviceabilityCheck`, `priceEstimate`, `matchAndPrice`,
`confirmPriceChoice`) are all thin `apiFetch` wrappers with no local price
arithmetic — the customer app only ever displays `price_snapshot`/
`selected_provider_price_options` fields verbatim from the server response.

## Not verified this round

- The full booking-summary/confirm/reference/detail steps for the
  `ac_installation` bargain path specifically (only match-and-price was
  re-run; Round 1 already proved the full chain end-to-end for the
  standard-price path). Deferred — the draft
  `d5048334-...` was left at `provider_matched` status, not confirmed into
  a booking, to avoid creating an unnecessary second real job record this
  round.
- Whether the confidential internal pricing-rule ID/base_price/min_price/
  max_price values are ever leaked into any user-facing copy across the 4
  apps — not audited this round (would require a UI-level review across
  Super Admin/Tenant/Customer screens, deferred).
