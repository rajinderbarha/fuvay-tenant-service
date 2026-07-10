# CUSTOMER-FRONTEND-01 — Live API Verification Report

Postgres and the FastAPI backend were both already running
(`pg_ctl status` reported the server up; `curl http://localhost:8000/health` -> 200)
so no restart was needed. All calls below used `curl.exe` against
`http://localhost:8000` with a real JWT.

## 1. Auth - PASS
```
POST /v1/auth/login  {"email":"customer@serviceos.in","password":"Password123!"}
-> 200, real access_token + refresh_token issued. JWT decodes to role=customer,
  aud=serviceos:customer, full_name="Demo Customer".
```
Source of seeded user: `SELECT id,email,role FROM users WHERE role='customer'` ->
one row, `customer@serviceos.in`.

## 2. Catalog - PASS
```
GET /v1/catalog/master/categories -> 200, real "Home Services" category
  (id 0888d283-9a52-4d7b-8612-9f47fa8357a1), is_customer_visible: true.
SELECT id,service_name,slug FROM master_services WHERE category_id=... -> real
  seeded services incl. "AC Installation" / slug ac_installation.
SELECT id,name FROM brands -> real seeded brands (Samsung, LG, Voltas, Blue Star, Daikin).
SELECT zipcode,city,tenant_id FROM tenant_service_areas -> real seeded zipcodes
  141001/141002 (Ludhiana), tenant 34b427a7-b2be-496c-b826-6d51bb181248.
```

## 3. Booking draft creation - PASS
```
POST /v1/customer/home-services/booking-drafts
  {"category_slug":"home_services","offering_slug":"ac_installation"}
-> 200, real draft created: id 86667924-7cde-4204-a0e0-3404a3994ca9,
  required_fields: ["issue_summary","city","brand_id"].
```
Note: the initial attempt with a guessed slug "ac-installation" (hyphenated)
correctly failed with 422 HOME_BOOKING_OFFERING_INVALID - confirms the backend
validates slugs against real catalog data rather than accepting anything.

## 4. Update draft fields - PASS
```
PUT /v1/customer/home-services/booking-drafts/{id}
  {issue_summary, city:"Ludhiana", zipcode:"141001", brand_id:<Samsung>,
   customer_name, customer_phone, address_snapshot}
-> 200, draft.status transitioned draft -> collecting_details.
```

## 5. Serviceability check - PASS (returned a real negative result)
```
POST /v1/customer/home-services/booking-drafts/{id}/serviceability-check
-> 200 {"serviceable": false, "available_provider_count": 0,
       "reason_code": "NO_PROVIDER_IN_ZIPCODE",
       "message": "This service is not available in Ludhiana yet. We're expanding soon!"}
```
This is a real, customer-safe message despite Ludhiana/141001 existing in
tenant_service_areas - meaning the seeded tenant's service area does not
translate into a bookable provider for AC Installation specifically (likely
missing package/enablement/bookability-status setup for that tenant+offering
combination, which is out of this sprint's strict scope to fix).

## 6. Provider-first matching - BLOCKED (real, honest failure)
```
POST /v1/customer/home-services/booking-drafts/{id}/match-and-price
-> 422 {"error_code":"HOME_BOOKING_NO_PROVIDER_AVAILABLE",
       "detail":"No eligible providers available in Ludhiana. Try a nearby city.",
       "request_id":"req_97d83eeb1673"}
```
This is a real request_id from a real error response - the exact shape the
frontend's ErrorBanner/parseError() is built to handle. No further zipcode
was available to retry against (only 141001/141002/blank were seeded), and
fixing the underlying provider-eligibility/bookability data is backend catalog
work outside this sprint's strict scope (frontend-only + minimal blocking fixes).

## 7. Booking creation, detail, tracking, review - NOT REACHED
Because matching never returned a provider, confirm-price-choice, /summary,
and /confirm (real booking creation) were never called live, so:
- No real booking_id was created.
- GET /v1/customer/bookings and /{id} and /{id}/tracking were not
  exercised against a real booking (only read against the code, not curl'd).
- Review submission (/rating) was not attempted - there is no completed
  booking to test against, and fabricating one was explicitly out of scope
  ("document honestly rather than fabricating one").

## Honest summary
Auth, catalog reads, draft creation, draft updates, and serviceability-check are
all confirmed working end-to-end against the real live backend + Postgres data.
Matching, pricing, booking confirmation, tracking, and review submission were
NOT confirmed against a real success response in this session - the dev
database's only servable zipcode/tenant combination did not produce a bookable
provider for AC Installation. This is the single biggest verification gap in
this sprint.
