# HS7 — API Mapping Report

Real routes differ from the ticket's suggested paths in several places.
Actual, live-verified routes:

| Ticket suggestion | Real route | Notes |
|---|---|---|
| `GET /v1/customer/home-services/catalog` | `GET /v1/catalog/master/categories`, `GET /v1/catalog/master/services?category_id=` | Pre-existing, real, populated. Used to resolve `category_slug`/`offering_slug` for Step 1. |
| `GET /v1/customer/home-services/catalog/{service_id}/questions` | `GET /v1/catalog/master/service-types`, `/brands`, `/issue-types` (all under `/v1/catalog/master/*`); also `/v1/customer/catalog/service-options`, `/issue-types` under `service_option_customer_router.py` | Two parallel customer catalog routers exist (`admin_catalog/customer_router.py` at `/v1/catalog/master/*` and `service_option_customer_router.py` at `/v1/customer/catalog/*`) — both real, not consolidated. Not exercised end-to-end this pass (see UI report — no frontend to drive this yet). |
| `POST /v1/home-services/matching/select-provider` | `POST /v1/customer/home-services/booking-drafts/{draft_id}/match-and-price` | Draft-scoped, not a standalone matching call — matches the ticket's own required flow (provider selection tied to a specific draft's collected fields). Live-verified. |
| `POST /v1/customer/home-services/bookings` | `POST /v1/customer/home-services/booking-drafts/{draft_id}/confirm` | Draft-to-booking confirmation, not a flat create. Live-verified, returns all ticket-required response fields (added this pass). |
| `GET /v1/customer/bookings` | `GET /v1/customer/bookings` | Matches. **Added this pass** — did not exist before (only detail + tracking existed). Live-verified. |
| `GET /v1/customer/bookings/{booking_id}` | `GET /v1/customer/bookings/{booking_id}` | Matches. Pre-existing, enriched this pass with provider/price/payment_mode. Live-verified. |
| `POST /v1/customer/bookings/{booking_id}/cancel` | Not found under this router; a `POST /{draft_id}/cancel` exists but only for pre-confirmation drafts | **Gap** — no cancel-a-confirmed-booking endpoint found for Home Services. Not built this pass (out of the time budget after the flow-blocking bugs). See Remaining Blockers. |
| `POST /v1/customer/bookings/{booking_id}/rating` | Not verified this pass | The platform has a real Review & Rating Engine (`/v1/reviews`, confirmed healthy in `/health`) — likely the real integration point, not checked against Home Services bookings specifically this pass. |

## Additive changes made this pass (no breaking changes)
- `GET /v1/customer/bookings` (list) — new endpoint.
- `GET /v1/customer/bookings/{booking_id}` — response gained `booking_id`,
  `address`, `selected_provider`, `selected_price_option`,
  `selected_price_amount`, `payment_mode`.
- `POST /v1/customer/home-services/booking-drafts/{id}/confirm` — response
  gained `booking_status`, `selected_provider_tenant_id`,
  `selected_price_option`, `selected_price_amount`, `payment_mode`.

## Verdict
API integration uses real data throughout (no mock data introduced). Two
gaps remain unimplemented: booking cancellation post-confirmation, and
rating submission — both documented, not fabricated.
