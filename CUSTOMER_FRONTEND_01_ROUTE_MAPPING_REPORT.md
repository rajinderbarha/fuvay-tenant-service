# CUSTOMER-FRONTEND-01 — Route Mapping Report

All spec routes were implementable as specified; no path changes were required.

| Spec route | Implemented route | File |
|---|---|---|
| /customer/home-services | /customer/home-services | frontend/customer-app/app/customer/home-services/page.tsx |
| /customer/home-services/book | /customer/home-services/book | frontend/customer-app/app/customer/home-services/book/page.tsx |
| /customer/bookings | /customer/bookings | frontend/customer-app/app/customer/bookings/page.tsx |
| /customer/bookings/:booking_id | /customer/bookings/[bookingId] | frontend/customer-app/app/customer/bookings/[bookingId]/page.tsx |
| /customer/bookings/:booking_id/rate | /customer/bookings/[bookingId]/rate | frontend/customer-app/app/customer/bookings/[bookingId]/rate/page.tsx |
| /customer/profile | /customer/profile | frontend/customer-app/app/customer/profile/page.tsx |

Additional routes added (not in spec list, required for the app to function):
- `/login` — frontend/customer-app/app/login/page.tsx — no customer-specific login route existed anywhere in the repo; created mirroring tenant-portal's `/login` convention, calling the same shared `/v1/auth/login` endpoint.
- `/` (root) — frontend/customer-app/app/page.tsx — redirects to `/customer/home-services` since Next.js requires a root route.

No deviation from the spec's route list was necessary.
