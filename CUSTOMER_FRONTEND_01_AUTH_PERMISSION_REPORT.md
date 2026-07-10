# CUSTOMER-FRONTEND-01 — Auth/Permission Report

## Real login endpoint used
No dedicated customer-only auth endpoint exists anywhere in the repo (searched
`app/engines/auth/*.py`, `app/engines/auth/router.py`). tenant-portal, provider,
staff, and customer all authenticate through the single shared
`POST /v1/auth/login` (`app/engines/auth/router.py`), which returns a JWT whose
`role` claim determines authorization elsewhere (verified live: decoded a real
token issued for `customer@serviceos.in` and confirmed `"role":"customer"`,
`"aud":"serviceos:customer"`).

`frontend/customer-app/lib/api/auth.ts` → `customerLogin()` calls this same
endpoint (mirroring exactly what `frontend/tenant-portal/app/login/page.tsx`
does for tenant/provider users), storing the token under
`serviceos_customer_token` / `serviceos_customer_refresh` / `serviceos_customer_id`
/ `serviceos_customer_name` in `localStorage` — a separate key namespace from
tenant-portal's `serviceos_tenant_*` keys, so both apps could theoretically run
in the same browser without clobbering each other's session.

## Guest browsing
`/customer/home-services` (catalog landing) does not require login — it calls
public catalog endpoints (`/v1/catalog/master/*`) with no auth header, matching
those endpoints' own `Depends(get_db)`-only signature (no `get_current_user`
dependency in `admin_catalog/customer_router.py`).

## Login required before booking
`handleServiceNext()` in the booking wizard checks `isLoggedIn()` before calling
`startBookingDraft()` (which requires `get_current_user` server-side anyway) and
redirects to `/login?next=/customer/home-services/book` if not authenticated.

## Own-bookings-only enforcement
All of `GET /v1/customer/bookings`, `GET .../{id}`, `GET .../{id}/tracking`,
`POST/GET .../{id}/rating` filter by `customer_id == uuid.UUID(user.user_id)`
server-side (confirmed by reading `home_service_assignment/customer_router.py`)
— accessing another customer's booking returns a 404-shaped
`{"success": false, "error": {"code": "BOOKING_NOT_FOUND", ...}}` payload (note:
HTTP 200 with a success:false body, not an HTTP 404 status — the frontend's
booking-detail page renders `detail.error.message` when this shape is present).
This was **not** live-tested against a second customer account (only one seeded
customer user exists: `customer@serviceos.in`) — documented as an untested gap.

## 401 / 403 handling
`apiFetch()` in `lib/api/client.ts` attempts a silent refresh-token retry on 401,
then clears the session and redirects to `/login` if that fails — mirroring
tenant-portal's `apiFetch` pattern exactly. 403 responses are surfaced through
`ErrorBanner`, which always includes `request_id` when the backend provides one
(see `parseError()`).

## Not live-tested
Refresh-token rotation, 403-on-forbidden-action, and cross-customer booking
access were not exercised live due to only one seeded customer account and time
constraints — flagged as gaps rather than claimed as verified.
