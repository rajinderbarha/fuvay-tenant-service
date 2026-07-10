# CUSTOMER-FRONTEND-02 — Browser Booking Flow Report (curl/code-review approximation, NOT real browser)

## Live curl walkthrough (repeat of Sprint-01 baseline against unchanged dev DB)

1. Login as customer@serviceos.in -> 200, real JWT.
2. `GET /v1/catalog/master/categories` -> 200, real "Home Services" category.
3. `GET /v1/catalog/master/brands` -> 200, real seeded brands (AO Smith, Aquaguard, Samsung, LG, Voltas, Daikin, etc).
4. `POST /v1/customer/home-services/booking-drafts {category_slug:"home_services", offering_slug:"ac_installation"}` -> 200, real draft `b168d115-e4d0-4c3d-83f0-00c6f6f90d40`.
5. `PUT .../booking-drafts/{id}` with issue_summary/city=Ludhiana/zipcode=141001/customer_name/phone -> 200, status draft -> collecting_details.
6. `POST .../booking-drafts/{id}/serviceability-check` -> 200 `{"serviceable":false,"reason_code":"NO_PROVIDER_IN_ZIPCODE"}` — real, customer-safe message.
7. `POST .../booking-drafts/{id}/match-and-price` -> **422 HOME_BOOKING_NO_PROVIDER_AVAILABLE**, real request_id `req_a467d0b1df23`.

**Same outcome as Sprint 01**: this dev database's seeded tenant/provider data does not produce a bookable provider for AC service in zipcode 141001/Ludhiana (or any other seeded zipcode). This is backend catalog/seed data, explicitly out of this sprint's strict frontend-only scope. Booking creation, tracking, and review submission against a real success response were therefore **not achievable live** in this session, same as Sprint 01.

Baseline price numbers (₹770/850/935) could not be verified against a real response for this reason — no live price payload was ever returned.

## Hard gates verified IN CODE (`app/customer/home-services/book/page.tsx`)

1. **Provider must appear before price UI renders** — the stepper renders `step === "provider"` (showing `ProviderCard`) strictly before `step === "price"`; the only way to reach `"price"` is `goto("price")`, called from `ProviderCard`'s `onNext` handler, which only renders once `matchResult.provider` exists. Confirmed at lines 266-280.
2. **Price is not manually editable** — `PriceStep` renders each tier as a `<div onClick={() => onSelect(t.key)}>` showing `₹{options[t.key]}` as plain text; there is no `<input>` bound to any price value anywhere in the file (grepped for `<input` — only found in the Details/Location steps for text fields, none touching price).
3. **Confirm button gated** — Originally the "Confirm Booking" button in `ReviewStep` was disabled only on `loading`, not on missing provider/price selection (a defensive gap, since normal step-flow already guarantees both are set by the time this step renders). **Fixed in this sprint**: now `disabled={loading || !priceTier || !(provider.provider_name || provider.business_name)}`.
4. **Payment copy** — grepped for "Pay Provider Directly": found at `app/customer/home-services/book/page.tsx:359` ("Payment: Customer Pays Provider Directly") and `app/customer/bookings/[bookingId]/page.tsx:35` (same copy on the tracking page). Matches required copy.

## Verdict
Code-level gating is sound (confirmed by reading the actual conditionals, not assumed). Live confirmation of a full successful booking-creation response was blocked by the same pre-existing backend seed-data gap documented in Sprint 01 — not a frontend defect, and not fixed here (out of strict scope). One real gating bug found and fixed (confirm button not defensively disabled).
