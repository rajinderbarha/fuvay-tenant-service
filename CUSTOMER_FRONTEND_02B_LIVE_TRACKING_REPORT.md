# CUSTOMER-FRONTEND-02B — Part 5: Live Tracking Report

## Real curl verification

`GET /v1/customer/bookings` (Customer One) returned both the new booking (BK-20260710-000002, status pending_assignment) and a pre-existing completed booking (BK-20260710-000001) — list renders provider name, price option/amount, no internal fields.

`GET /v1/customer/bookings/{id}` (detail) returned:
```json
{
  "status": "pending_assignment",
  "assignment_status": "unassigned",
  "assignment_message": "Provider is assigning a technician.",
  "selected_provider": {"provider_name": "Demo AC Services", "rating": null, "public_badges": ["Verified","High Completion"]},
  "selected_price_option": "mid",
  "selected_price_amount": 850.0,
  "payment_mode": "customer_pays_provider_directly",
  "job_status": "pending_assignment"
}
```

`GET /v1/customer/bookings/{id}/tracking` returned a timeline (`[{event: "Booking confirmed", status: "confirmed"}]`) plus assignment status/message.

## Customer-safety check (source code + live payload)
`_customer_safe_provider()` in `app/engines/home_service_assignment/customer_router.py` explicitly whitelists only `provider_name, rating, public_badges` from the provider snapshot — confirmed no internal_score/matching_score_snapshot/admin price range ever reaches these responses (verified both by reading the source and by inspecting the live JSON, which contains none of those fields).

## Frontend rendering (verified live via Playwright, see BROWSER_E2E_REPORT)
- `/customer/bookings` list and `/customer/bookings/[bookingId]` detail page both render using only the above real API fields.
- "Pay Provider Directly" / "Customer Pays Provider Directly" copy renders on the booking confirmation and review screens (verified in the passing browser test's assertion `expect(page.getByText(/Pays Provider Directly/))`).
- Forbidden-term scan of the rendered confirmation + tracking page text (30+ internal/ledger/audit/commission/etc. terms) found ZERO matches — enforced as a hard assertion inside the Playwright test itself (not just a static grep).

## Job status advance
No staff/technician action was driven in this part (Part 6 handles job-lifecycle transitions using a booking that was already `completed` from a prior sprint's fixture data); this part's scope (tracking render + no-leak check) is fully verified live.

STATUS: LIVE TRACKING SUCCESS.
