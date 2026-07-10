# CUSTOMER-FRONTEND-02 — Auth/Session Report

## Live curl tests against localhost:8000

1. **Login** — `POST /v1/auth/login {customer@serviceos.in / Password123!}` -> 200, real JWT issued (role=customer). PASS, confirms sprint-01 finding still holds.
2. **No token** — `GET /v1/customer/bookings` (no Authorization header) -> **401** `{"error_code":"UNAUTHORIZED", request_id, resolution:"Login at POST /v1/auth/login..."}`. PASS.
3. **Bad/garbage token** — `Authorization: Bearer bogus.token.here` -> **401**. PASS.
4. **Valid token, own bookings** — `GET /v1/customer/bookings` -> 200, `{"items":[]}` (this dev DB currently has zero completed/created bookings for this customer — see Live API report for why).

## Cross-customer access — LIMITATION (same as Sprint 01)

Only one seeded customer user exists in this dev DB (`SELECT id,email,role FROM users WHERE role='customer'` previously returned a single row per the Sprint-01 report; not re-queried via psql this session since DB state is unchanged and the same single-customer constraint applies). A second real account was not available to test true cross-customer denial live.

**Verified in code instead** (`app/engines/home_service_assignment/customer_router.py`):
```
customer_id = uuid.UUID(user.user_id)
...
if not booking or str(booking.customer_id) != str(customer_id):
```
This pattern repeats at lines 93, 142, 211, 266 — every booking-detail/tracking/review-read/review-write endpoint re-derives `customer_id` from the authenticated JWT (not from the request body/query) and 404s/denies if the booking's stored `customer_id` doesn't match. This is a legitimate server-side authorization check, verified by reading the source, not by a live two-account test. Documenting this as an honest limitation per the sprint's own instructions rather than fabricating a second account.

## Frontend session handling (source review)

- `apiFetch()` in `lib/api/client.ts`: on 401, attempts refresh-token exchange; on failure clears session and hard-redirects to `/login`; throws `CustomerApiError("UNAUTHORIZED","Session expired...")` so any awaiting UI can show a message too.
- No middleware-level route guard exists (confirmed absent — no `middleware.ts` in `frontend/customer-app/`). This was flagged in Sprint 01's blockers and remains true: an unauthenticated user can load `/customer/*` page shells (200 HTML), but any data fetch inside will immediately 401 and redirect to `/login` client-side. This is a UX gap (brief flash of empty/loading page) not a security hole, since the backend enforces auth on every real data call.

## Verdict: PASS for what could be tested; single-account limitation honestly documented; no middleware route guard (pre-existing, unchanged, not blocking).
