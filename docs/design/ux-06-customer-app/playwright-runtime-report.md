# Playwright Runtime Report — UX-06 Round 4

Real Chromium (headless, 390px viewport) against a real Expo web dev server
(port 19006, CORS-allowlisted) and the live backend, real seeded customer
(`customer@serviceos.local`).

## Steps that genuinely fired against real backend calls this round

Real login, real Home, real Bookings/Profile tab render, real chat-session
creation, real chat-scoped language selector (Hindi selected), real 14
categories via `GET /v1/customer/categories`, real offering fetch for the
selected canonical category, real issue/address collection, **real
serviceability success** (NEW — was blocked in Round 3), **real price
response ₹82, `source: backend_catalog`** (NEW — was blocked in Round 3).

## Steps not reached

Booking review's confirm action correctly surfaces a real backend error
(`FINAL_DRAFT_NOT_READY`) rather than fabricating a confirmation — booking
reference, bookings list (with new data), booking detail, and refresh-
persistence of a real booking were therefore not reachable this round. This
is proven honestly blocked (see booking-submission-live-evidence.md), not
silently skipped.

## Console/errors

Zero uncaught page errors this round (Round 3's two runtime-crash bugs did
not recur). One cosmetic React key-prop warning — see console-runtime-report.md.

## Not attempted this round (time-boxed out)

Duplicate-submit-prevention proof via the actual UI (the unit test in
`bookingContract.test.ts` proves the idempotency-key mechanism at the request
layer; a full UI double-click race condition was not exercised in the
browser), dark-theme persistence (no dark theme exists — see
light-dark-runtime-report.md), Notifications screen, Booking Detail screen.
