# HS7 — Booking Creation Report

## Real backend booking creation — live-verified

`POST /v1/customer/home-services/booking-drafts/{draft_id}/confirm`
(idempotent via `Idempotency-Key` header) creates a real `ServiceBooking`
+ `ServiceJob` pair. Live-verified twice against the real database with
two independent drafts (AC Repair / Split AC / LG / Ludhiana 141001),
producing `BK-20260709-000001` (mid, ₹850) and `BK-20260709-000002`
(low, ₹770).

Response shape now includes all ticket-required fields (added this pass
— previously missing `selected_provider_tenant_id`, `selected_price_option`,
`selected_price_amount`, `payment_mode`, `booking_status`):

```json
{
  "booking_id": "a3e533c2-...",
  "booking_number": "BK-20260709-000001",
  "booking_status": "confirmed",
  "selected_provider_tenant_id": "34b427a7-...",
  "selected_price_option": "mid",
  "selected_price_amount": 850.0,
  "payment_mode": "customer_pays_provider_directly"
}
```

## Backend validation — live-verified

| Requirement | Result |
|---|---|
| Cannot confirm without selected provider | Enforced — `mark_ready_for_confirmation` raises `HOME_BOOKING_NO_PROVIDER_AVAILABLE` if `draft.selected_tenant_id` is unset |
| Cannot confirm without selected price option | Enforced — raises `INVALID_SELECTED_PRICE_OPTION` if no tier was confirmed |
| Selected provider must still be bookable at confirm time | **Live-verified**: flipped `provider_visibility_statuses.is_bookable` to `false` after price choice, called `/confirm` → `422 SELECTED_PROVIDER_NOT_BOOKABLE`. Restored after. |
| Selected price amount cannot be client-modified | Structurally enforced — see `HS7_PRICE_SELECTION_REPORT.md` |
| Payment mode is always `customer_pays_provider_directly` | Hardcoded constant in `finalize()`'s response and in the persisted `price_snapshot` — never configurable for Home Services |
| Idempotent retry returns existing booking, not an error | **Live-verified**: retrying `/confirm` with the same `Idempotency-Key` after a successful booking returned `{"idempotent": true, "booking_number": "BK-...-000001", ...}` |
| All errors include `request_id` | Confirmed on every error response captured this pass (RFC 7807 `problem+json`, established platform-wide contract) |

## Bugs found and fixed this pass
1. `mark_ready_for_confirmation` was dead code (never wired) — see main flow report.
2. 4 tables missing `updated_at` blocked every step of this endpoint's write path — see main flow report.
3. Idempotent-retry regression introduced by fix #1's naive wiring (calling
   `mark_ready_for_confirmation` unconditionally re-hit the terminal-status
   guard on retry) — fixed by skipping that call when the draft is already
   `confirmed`, live-verified the retry now returns the idempotent result.

## Not persisted to `ServiceBooking` (documented gap)
`selected_price_option`/`selected_price_amount`/`payment_mode` are stored
inside `ServiceBooking.price_snapshot` (a JSONB blob), not as first-class
columns. This is sufficient for the customer-facing list/detail/tracking
endpoints (which read from `price_snapshot`), but any future reporting
that expects a dedicated `payment_mode` column would need a migration —
noted, not built, since no such consumer exists yet.

## Verdict
Booking creation: **working, validated, live-verified.** Not
`NOT_READY_HS7_BOOKING_API_FAILED`.
