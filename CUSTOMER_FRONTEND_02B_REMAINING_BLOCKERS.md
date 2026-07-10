# CUSTOMER-FRONTEND-02B — Remaining Blockers

## Resolved this sprint (previously blocking, now fixed)
1. No real browser E2E existed — now exists and passes (2/2) using system Chrome via Playwright `channel: 'chrome'`.
2. Seeded tenant/zipcode combo did not produce a bookable provider match — fixed via two targeted SQL backfills (LG brand + "AC Not Cooling" issue type category_id/master_service_id, both previously NULL, blocking category-scoped catalog queries). Real matching now returns Low ₹770/Mid ₹850/High ₹935 as specified.
3. Only one customer account existed — Customer Two (`customer2@serviceos.in`) was found to already exist from a prior session; verified login and used for two-customer access-control testing.
4. No completed booking existed for review testing — a completed booking (`BK-20260710-000001`) was found already present from a prior sprint's fixture data; used directly for live review + duplicate-review + browser rate-page verification (see Part 6 report for why this fallback was used instead of re-driving the full staff/technician lifecycle).

## Frontend bugs found and fixed during this sprint (all in `frontend/customer-app`)
1. `getCatalogServiceTypes()` destructured `{service_types}` instead of the real API's `{types}` key.
2. `CatalogBrand` interface used `id` instead of the real API's `brand_id` field — brand selection silently failed to send `brand_id` to the backend, breaking booking confirmation ("Missing required fields: brand_id").
3. `PriceStep`/`ReviewStep` read `price_options.{low,mid,high}` instead of the real API's `selected_provider_price_options.{low_price,mid_price,high_price}` — price cards never rendered real numbers.
4. The booking wizard had no "Type" (Split AC/Window AC) selection step at all, so `offering_type_id` was never sent, and type+brand-keyed pricing rules could never resolve.

All four were genuine frontend/backend contract mismatches (the backend was correct in every case); all four are now fixed and covered by the passing browser E2E test.

## Known non-blocking gaps (pre-existing, out of this sprint's scope)
1. **Cancel-after-confirmation**: no real backend endpoint exists for cancelling an already-confirmed booking (only pre-confirmation draft cancel exists). Documented in the frontend's own `lib/api/customer-home-services.ts`. Building this is backend engine work, out of CF-02B's frontend-fix scope.
2. **`npm run lint`**: `next lint` fails with "Invalid project directory provided" — this Next.js 16 project has no working ESLint config wired (pre-existing, not introduced this sprint). Fixing would require authoring an ESLint config, not a customer-frontend bug fix; treated as non-blocking per the spec's "if configured" qualifier.
3. **Photo upload on booking draft**: intentionally disabled with an explanatory note in the UI (not wired to a live endpoint) — pre-existing, documented, out of scope to build in this sprint.
4. **Cross-customer booking-detail access control** uses an HTTP-200-with-inline-error envelope (not a 403/404 status) for both "not found" and "not yours" — this is existing, intentional non-enumeration behavior in the backend, not a new gap, and was verified to correctly hide the booking's existence from Customer Two either way.

No blockers remain that were in this sprint's assigned scope.
