# HS7 — Customer Booking UI Report

## Status: not built this pass

No customer-facing web frontend exists in this repository. The two
Next.js apps present — `frontend/super-admin` and `frontend/tenant-portal`
— are, respectively, the platform admin console and the tenant/provider
operations portal. Neither serves a `/customer/*` route.

The actual customer surface is `mobile/customer-app` (React Native).
Its relevant screens (`BookServiceScreen.tsx`, `AIChatScreen.tsx`,
`ChatScreen.tsx`, `SmartBotScreen.tsx`) are static/hardcoded — they use a
local `SERVICE_CATEGORIES` constant and call a generic `bookingsApi.create`,
never the real `home_service_booking` draft API
(`start_booking_draft` → `match-and-price` → `confirm-price-choice` →
`confirm`) that HS6/HS6B/this pass certified and fixed.

## Why this wasn't attempted this pass
Running the real backend flow end-to-end for the first time (rather than
assuming Sprint 16/HS6/HS6B's prior static/partial verification meant it
worked) surfaced 6 real, flow-blocking bugs (see
`HS7_CUSTOMER_BOOKING_FLOW_REPORT.md`) — the entry point, the
serviceability gate, and the confirmation step were each independently
broken. Fixing those and live-verifying the corrected flow against the
real database consumed this pass's full time budget. Building a new
frontend (whether a `frontend/customer-portal` Next.js app matching the
ticket's literal `/customer/home-services` route style, or rewiring the
existing React Native screens) is untouched.

## Recommendation for the next pass
Given the codebase's established pattern (Next.js for every other
surface), the ticket's route naming (`/customer/home-services`,
`/customer/bookings/:booking_id`) reads as a web-app convention, not a
mobile-navigation one. Wiring the existing `mobile/customer-app` screens
to the (now fixed) real API is the smaller, more consistent-with-current-
architecture option; building a new `frontend/customer-portal` Next.js
app is the literal-route-match option. This decision should be made
explicitly with the user before the next HS7 continuation, rather than
assumed.

## Verdict
UI: **not implemented**. All 12 UI-facing acceptance items (service
selection cards, question steps, location form, matching loading state,
provider card, price cards, review screen, confirmation screen, booking
list/detail, forbidden-label scan on UI, NaN/null/undefined scan on UI,
TypeScript/build/lint) are unverified because no UI exists to check them
against. This is the primary reason for this pass's `PARTIAL_READY`
recommendation.
