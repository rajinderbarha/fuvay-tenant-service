# HS7 — Customer-Safe Data Report

## Bugs found and fixed this pass

1. **`internal_score` and `matching_score_snapshot` leaked directly to the
   customer** via two live-verified response paths:
   - `POST /{draft_id}/confirm-price-choice` — `booking_summary.matching_score_snapshot`
     included the full per-signal breakdown (`health_score`, `capacity_score`,
     `distance_score`, `availability_score`, `cancellation_score`,
     `service_match_score`, `job_completion_score`, `rating_score`).
   - `POST /{draft_id}/summary` — `booking_summary.selected_provider.internal_score`
     (a raw numeric ranking score) and the same `matching_score_snapshot`.

   Both are direct violations of the ticket's hard gate ("Do not show
   customer internal admin pricing or provider scoring"). Fixed:
   `confirm_price_choice` no longer copies `matching_score_snapshot` into
   `booking_summary` at all; `build_booking_summary` now strips
   `internal_score`/`matching_score_snapshot` from the provider snapshot
   before returning it. Live-verified clean after the fix — `/summary`'s
   `selected_provider` now contains only `tenant_id`, `provider_name`,
   `rating`, `public_badges`, `customer_visible_reason`.

## Verified clean (no fix needed)
- `selected_provider` on the customer booking list/detail endpoints
  (`GET /v1/customer/bookings`, `GET /v1/customer/bookings/{id}`) —
  the new `_customer_safe_provider()` helper added this pass explicitly
  allow-lists `provider_name`/`rating`/`public_badges` only.
- `match-and-price`'s direct response — `HomeServiceChatbotBookingService.match_provider_and_price`
  only includes `selected_provider_admin`/internal score when the caller
  has `reveal_internal_score=True`, which the customer router never
  passes (hardcoded `False`).
- `area_market_comparison` — aggregate-only (min/avg/max/count), no
  per-competitor identity ever returned.
- No `admin_min`/`admin_max`/commission/usage-credit/security-deposit
  fields appear anywhere in the customer-facing response paths exercised
  this pass.

## Not scanned this pass
No frontend UI exists to scan for forbidden labels rendered client-side
(see `HS7_CUSTOMER_BOOKING_UI_REPORT.md`) — this report covers only the
real API response payloads, which is the layer that actually matters for
"can the customer's browser/app receive this data," but a UI-level scan
is still required once a frontend exists.

## Verdict
Customer-safe data (API layer): **fixed and live-verified clean.** Not
`NOT_READY_HS7_CUSTOMER_SAFETY_FAILED` for the backend. UI-level scan
pending frontend build.
