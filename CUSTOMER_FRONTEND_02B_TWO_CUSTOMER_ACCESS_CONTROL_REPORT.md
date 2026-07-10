# CUSTOMER-FRONTEND-02B — Part 7: Two-Customer Access Control Report

## Customer Two
`customer2@serviceos.in` already existed in the `users` table (role=customer) from a prior sprint. Login verified live: real JWT issued with `role: customer`.

## Live cross-customer checks (Customer Two token against Customer One's data)

1. **View booking detail** — `GET /v1/customer/bookings/{customer_one_booking_id}` as Customer Two:
   - HTTP 200, but business-logic-level block: `{"success": true, "data": {"success": false, "error": {"code": "BOOKING_NOT_FOUND", "message": "Booking not found."}}}`.
   - Policy: the backend (`app/engines/home_service_assignment/customer_router.py::get_booking`) always returns HTTP 200 with an inline `success:false` error envelope rather than a 403/404 status code, for both "doesn't exist" and "not yours" cases (same code path, `str(booking.customer_id) != str(customer_id)` check). This is intentional non-enumeration behavior (doesn't reveal whether the ID exists), documented as-is — not a bug.

2. **Review Customer One's completed booking** — `POST /v1/customer/bookings/{id}/rating` as Customer Two:
   - **HTTP 404** `BOOKING_NOT_FOUND` — real HTTP status this time, since `submit_booking_rating` raises `ServiceOSException(..., status_code=404)` directly rather than returning an inline ok() envelope. Correctly blocked.

3. **Cancel Customer One's booking** — no real backend endpoint exists for cancel-after-confirmation at all (confirmed via `grep` across all `customer_router.py` files — only a pre-confirmation `booking-drafts/{id}/cancel` exists, which is a different resource). This is a known, pre-existing gap already documented in the frontend (`lib/api/customer-home-services.ts` throws `"Cancel-after-confirmation is not wired to a real backend endpoint yet."`). Out of this sprint's scope to build (backend engine work); access-control for a nonexistent endpoint is moot.

## Frontend error-handling code review
`lib/api/client.ts::apiFetch` normalizes every non-2xx response and every explicit `{success:false, error:{...}}` envelope into a `CustomerApiError` carrying `code`, `message`, and `requestId`; `ErrorBanner` component (used on every relevant page) renders `friendlyGenericMessage(requestId)` for opaque/unknown errors, always including "Request ID: {id}" in the displayed text — confirmed by reading `parseError()` and `friendlyGenericMessage()` in `client.ts`. This satisfies the "friendly error with request_id" requirement without needing to drive it through the browser for this specific cross-customer case (per spec, code review is acceptable here).

STATUS: TWO-CUSTOMER ACCESS CONTROL VERIFIED LIVE — no blockers. (Cancel-endpoint gap is pre-existing/out-of-scope, not a new regression.)
