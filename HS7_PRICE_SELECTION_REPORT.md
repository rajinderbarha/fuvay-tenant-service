# HS7 — Price Selection Report

## Result: structurally cannot be manipulated by the customer

`POST /{draft_id}/confirm-price-choice` accepts only `price_tier: "low"|
"mid"|"high"` — there is no amount field in the request contract at all.
The backend resolves the exact amount from `draft.price_snapshot.price_options`
(computed server-side during `/match-and-price`) via
`resolve_customer_offer_for_tier()`. A customer sending an unrecognized
tier value gets a real, live-verified 422:

```json
{"error_code": "INVALID_PRICE_TIER", "detail": "price_tier must be 'low', 'mid', or 'high'."}
```

Live-verified with `{"price_tier": "custom", "amount": 1}` — the extra
`amount` field is silently ignored (never read anywhere in
`confirm_price_choice`), and the invalid tier is rejected.

## Booking creation carries only the resolved server amount
`finalize()`'s response and the persisted `ServiceBooking.price_snapshot`
both source `selected_price_amount` from `draft.booking_summary["customer_offer"]`
— the value `resolve_customer_offer_for_tier` computed — never from
anything the client sent to `/confirm`. There is no code path by which a
client-supplied amount reaches the booking record.

## Bug found and fixed this pass
`build_booking_summary` (the Review-step endpoint, called between price
choice and confirmation per the ticket's step order) previously
**overwrote** `draft.booking_summary` wholesale, destroying the
`selected_price_tier`/`customer_offer` that `confirm_price_choice` had
just written. This would have made `/confirm` fail with
`INVALID_SELECTED_PRICE_OPTION` after a completely legitimate price
selection. Fixed to merge onto the existing summary. Live-verified: after
the fix, `/summary` called after `/confirm-price-choice` correctly
preserves `selected_price_tier: "mid"` and reports
`ready_for_confirmation: true`.

## Verdict
Price selection: **enforced correctly.** Not
`NOT_READY_HS7_PRICE_SELECTION_FAILED` — the customer cannot edit price
manually by any live-verified path.
