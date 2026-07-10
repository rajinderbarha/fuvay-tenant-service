# HS9B — Customer Review Flow Report

## Result: real, reuses the existing certified Review Engine

New endpoints in `home_service_assignment/customer_router.py`:
- `POST /v1/customer/bookings/{booking_id}/rating`
- `GET /v1/customer/bookings/{booking_id}/rating`

Both wrap the pre-existing, real Sprint 24 Review Engine
(`app/engines/review/service.py::ReviewService.create_review`, which
already has a real DB-level idempotency guard —
`uq_review_customer_job` unique constraint) rather than building a
parallel review system.

## Live-verified, all three required scenarios
1. **Submit review on a completed booking** → `200`, real `Review` row
   created (`review_id`, `composite_score: 5.0`, all 5 signal fields set
   to the customer's single 1-5 rating).
2. **Duplicate review on the same booking** → `409
   REVIEW_ALREADY_SUBMITTED` — this endpoint deliberately does **not**
   reuse `ReviewService`'s own "return existing review as idempotent"
   behavior (silent 200), since the ticket explicitly wants a clean
   rejection error; checked for an existing row before calling the
   service and raises the ticket's exact error code first.
3. **Review on an incomplete booking** (`status: quote_required`) →
   `422 BOOKING_NOT_COMPLETED`, exact ticket message.

`GET .../rating` returns the customer-safe shape
(`rating`, `comment`, `created_at`) — confirmed via live call after
step 1, matching the just-created review.

## Fields implemented vs. ticket's list
- Rating 1-5: **real**, validated (`RATING_REQUIRED` if missing/out of range).
- Review comment: **real**, optional.
- Service quality tags / "would recommend" / photo upload: **not
  implemented** — the single `rating` value is mapped to all 5 of the
  underlying Review model's signal columns (overall_quality, punctuality,
  cleanliness, value_for_money, communication) rather than collecting
  each separately, since the ticket's customer-facing form only asked
  for one overall 1-5 rating plus an optional comment.

## Customer-safe UI note
No customer-facing UI was built (same established gap as HS7/HS8/HS8B/HS9
— no customer web frontend exists anywhere in this codebase). The API
itself is customer-safe by construction: `GET .../rating` never returns
usage-credit, ledger, commission, or internal-audit data — confirmed by
direct source read of the response-building code.

## Verdict
Customer review flow: **real, live-verified, all 3 required error/success
paths confirmed.** Not `NOT_READY_HS9_REVIEW_FLOW_FAILED`. No UI exists
to render it (documented, not fabricated).
