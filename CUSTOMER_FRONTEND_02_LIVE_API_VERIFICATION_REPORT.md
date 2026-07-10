# CUSTOMER-FRONTEND-02 — Live API Verification Report

Postgres + FastAPI backend were already running at :8000 (`curl /health` -> 200); customer-app dev server was started fresh this session (`npm run dev`, port 3002 per package.json).

| Step | Result |
|---|---|
| Login (customer@serviceos.in) | PASS — 200, real JWT |
| Catalog load (`/v1/catalog/master/categories`, `/brands`) | PASS — real seeded data (Home Services category; AO Smith/Aquaguard/Samsung/LG/Voltas/Daikin brands) |
| Booking draft creation | PASS — real draft `b168d115-e4d0-4c3d-83f0-00c6f6f90d40` created for `ac_installation` |
| Draft field update (issue/city/zipcode/name/phone) | PASS — status transitioned draft -> collecting_details |
| Serviceability check | PASS (real negative result) — `{"serviceable":false,"reason_code":"NO_PROVIDER_IN_ZIPCODE"}` |
| Provider matching (`match-and-price`) | **FAIL (real, honest)** — 422 `HOME_BOOKING_NO_PROVIDER_AVAILABLE`, request_id `req_a467d0b1df23` |
| Low/Mid/High pricing | NOT REACHED — matching never returned a provider, so no price payload was ever produced |
| Booking creation | NOT REACHED |
| Booking detail read | NOT REACHED for a real created booking (customer's `GET /v1/customer/bookings` returns `{"items":[]}` — zero bookings exist for this account in this dev DB) |
| Tracking read | NOT REACHED (no real booking exists) |
| Review submission | NOT REACHED (no completed booking exists) — no fabrication performed per spec |

## Root cause (unchanged from Sprint 01)
The dev database's only seeded serviceable zipcode/tenant combination (141001/141002, Ludhiana, tenant `34b427a7-...`) does not have an eligible/bookable provider set up for the `ac_installation` offering. This is backend catalog/provider-enablement seed data — explicitly out of this sprint's strict "customer frontend + minimal blocking fixes" scope. It was not re-investigated or fixed here because doing so would mean editing backend provider-enablement/bookability tables, which the spec's strict-scope section explicitly excludes ("Do not work on: ... backend engine redesign").

## Honest summary
Everything up through serviceability-check is proven live against the real backend + real Postgres data, exactly as in Sprint 01 (data unchanged since then). Matching, pricing, booking creation, tracking, and review remain unverified against a real success response — this is the single largest verification gap, carried over unresolved because its root cause is backend seed data outside this sprint's permitted scope.
