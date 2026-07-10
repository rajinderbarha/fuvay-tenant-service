# CUSTOMER-FRONTEND-01 — API Mapping Report

All endpoints below were confirmed by reading the actual router source files, not
the spec's illustrative JSON. The spec's illustrative example
`POST /v1/home-services/matching/select-provider` does **not** exist; the real
endpoint is `POST /v1/customer/home-services/booking-drafts/{draft_id}/match-and-price`.

## Catalog (read-only, public/customer)
Source: `app/engines/admin_catalog/customer_router.py` (prefix `/v1/catalog/master`)
- `GET /v1/catalog/master/categories` — active categories only (`is_active=True` enforced server-side)
- `GET /v1/catalog/master/services?category_id=` — active master services
- `GET /v1/catalog/master/brands?category_id=`
- `GET /v1/catalog/master/service-types?category_id=`
- `GET /v1/catalog/master/issue-types?category_id=&master_service_id=`
- `GET /v1/catalog/master/service-options?category_id=&master_service_id=`
- `GET /v1/catalog/master/flow/config?category_id=&service_id=` — backend-driven required-step flags (requires_brand, requires_issue_type, etc.)

Live-verified: `GET /v1/catalog/master/categories` returned real seeded "Home Services" category with `is_customer_visible: true`.

## Booking draft flow
Source: `app/engines/home_service_booking/customer_router.py` (prefix `/v1/customer/home-services/booking-drafts`), all endpoints require `get_current_user` (customer JWT).
- `POST /v1/customer/home-services/booking-drafts` — start draft — body `{category_slug, offering_slug}` — response key is `id`, **not** `draft_id` as the spec's illustrative shape suggested (verified live).
- `PUT /v1/customer/home-services/booking-drafts/{draft_id}` — update fields (issue_summary, brand_id, city, zipcode, customer_name, customer_phone, address_snapshot)
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/serviceability-check`
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/match-and-price` — THE real provider-first matching + price call. Backend selects exactly one provider server-side; no list is ever returned to the customer.
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/confirm-price-choice` — body `{price_tier: "low"|"mid"|"high"}` only, never a raw amount
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/summary`
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/confirm` — creates the real ServiceBooking + ServiceJob (idempotent via `Idempotency-Key` header)
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/cancel`
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/photos`
- DEPRECATED and NOT used by this app: `/match-providers`, `/select-provider` (list-based manual selection — explicitly marked deprecated in source, superseded by `/match-and-price`).

## Bookings list / detail / tracking / rating
Source: `app/engines/home_service_assignment/customer_router.py` (prefix `/v1/customer/bookings`)
- `GET /v1/customer/bookings` — list, paginated
- `GET /v1/customer/bookings/{booking_id}` — detail, includes `_customer_safe_provider()` (only provider_name/rating/public_badges — internal_score etc. never returned)
- `GET /v1/customer/bookings/{booking_id}/tracking` — customer-safe timeline built from `_safe_event_label()` mapping
- `POST /v1/customer/bookings/{booking_id}/rating` — submit review, wraps `app.engines.review.service.ReviewService`, enforces `BOOKING_NOT_COMPLETED` (422) and `REVIEW_ALREADY_SUBMITTED` (409) with request_id
- `GET /v1/customer/bookings/{booking_id}/rating` — fetch existing review

## Deviation from spec's `submitCustomerBookingReview`/generic review engine
The spec also names a generic `/v1/customer/reviews` engine (`app/engines/customer_reviews/customer_router.py`), which uses `record_type`/`record_id` and is a separate, more general review system (used elsewhere in the platform, e.g. non-Home-Service verticals). For Home Services bookings specifically, the wired, booking-shaped review path is `/v1/customer/bookings/{booking_id}/rating` above, and that is what `lib/api/customer-home-services.ts` calls. This was a deliberate choice to use the real wired path rather than force-fit the generic engine.

## No dedicated "service questions" endpoint
No endpoint resembling `getCustomerServiceQuestions(serviceId)` (single/multi/text/photo admin questions) was found wired for customer Home Services booking. The nearest real substitute is `flow/config`'s `requires_*` flags plus `service-options`. Documented as a gap in CUSTOMER_FRONTEND_01_REMAINING_BLOCKERS.md.

## No live cancel-after-confirmation endpoint
`app/engines/home_service_assignment/customer_router.py` has no `/v1/customer/bookings/{id}/cancel` route (only the pre-confirmation booking-draft `/cancel` exists). `cancelCustomerBooking()` in the API module throws a clear "not wired" error rather than faking success — documented as a gap.

## Auth
`POST /v1/auth/login` (`app/engines/auth/router.py`) — the same shared endpoint tenant-portal uses. Live-verified: a seeded user `customer@serviceos.in` / `Password123!` with `role="customer"` logs in through this endpoint; JWT audience is `serviceos:customer`.
