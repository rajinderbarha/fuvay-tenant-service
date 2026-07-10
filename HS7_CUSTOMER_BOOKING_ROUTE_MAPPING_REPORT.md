# HS7 — Customer Booking Route Mapping Report

No customer-facing web frontend exists in this repository (see
`HS7_CUSTOMER_BOOKING_UI_REPORT.md`), so none of the ticket's suggested
frontend routes (`/customer/home-services`, `/customer/home-services/book`,
`/customer/bookings`, `/customer/bookings/:booking_id`, `/customer/profile`)
exist yet. This report maps the **backend API surface** that a future
frontend (web or the existing `mobile/customer-app`) would call for each
route; see `HS7_API_MAPPING_REPORT.md` for the full endpoint-level detail.

| Ticket route | Backend support today |
|---|---|
| `/customer/home-services` (catalog) | `GET /v1/catalog/master/categories`, `/services` — real, ready |
| `/customer/home-services/book` (wizard) | `POST/PUT/GET /v1/customer/home-services/booking-drafts/*` — real, fixed and live-verified this pass |
| `/customer/bookings` (list) | `GET /v1/customer/bookings` — **added this pass**, real, live-verified |
| `/customer/bookings/:booking_id` (detail) | `GET /v1/customer/bookings/{id}` + `/tracking` — real, enriched and live-verified this pass |
| `/customer/profile` | Not investigated this pass — out of HS7's stated focus (service selection → booking confirmation → tracking), no profile-specific requirement in the ticket body beyond the route being listed |

## Verdict
Backend is route-ready for a future frontend to consume 4 of the 5 listed
areas; `/customer/profile` wasn't in scope of the 8-step flow this ticket
actually describes and wasn't investigated.
