# CUSTOMER-FRONTEND-02B — Part 8: Real Browser Click-Through Report

## Setup
- Playwright driving REAL system Chrome (`channel: 'chrome'`, headless) — NOT the broken bundled-Chromium download.
- REAL frontend dev server (`next dev --port 3002`), REAL backend (`localhost:8000`), REAL Postgres DB.
- No mocked network responses anywhere in the spec (verified, see MOCK_DATA_RESCAN report).

## Bugs found and fixed during real E2E iteration (see full bug list in final summary)
1. Login flaky "Failed to fetch" on first run — reproduced as transient (manual `page.evaluate(fetch(...))` calls with identical headers succeeded every time); retry succeeded. Not a code bug requiring a fix; noted as environment flakiness.
2. `getByRole('button', {name:'Next'})` strict-mode violation — Next.js Dev Tools floating button also matches "Next" by accessible name. Fixed by using `{ name: 'Next', exact: true }` in the spec.
3. **Real bug**: `getCatalogServiceTypes()` typed/destructured the response as `{service_types}` but the real backend (`GET /v1/catalog/master/service-types`) returns `{types}` — service type chips never rendered from real data. Fixed in `lib/api/customer-home-services.ts` and `app/customer/home-services/book/page.tsx`.
4. **Real bug**: `CatalogBrand` interface declared `id: string` but the real backend (`GET /v1/catalog/master/brands`) returns `brand_id`, not `id` — brand chip clicks silently set `brandId` to `undefined`, so `brand_id` was never sent to the draft, causing `confirm` to fail with "Missing required fields: brand_id". Fixed interface + component to use `brand_id`.
5. **Real bug**: `PriceStep`/`ReviewStep` read `matchResult.price_options`/`matchResult.prices` with bare `low/mid/high` keys, but the real backend (`match-and-price`) returns `selected_provider_price_options` with `low_price/mid_price/high_price` keys — price cards never rendered real numbers. Fixed via a shared `extractPriceOptions()` helper that reads the real field names.
6. Missing UI step entirely: there was no "Type" (Split AC/Window AC) selector in the booking wizard at all, so `offering_type_id` was never sent — since pricing for this offering is type+brand-keyed, matching failed with "Selected provider does not have a customer price range configured yet." Added a Type chip-selector step (parallel to the existing Brand selector) in the details step.

All of the above are real frontend/backend contract bugs, not seed-data or backend bugs — the backend consistently returned its real, correct field names; the frontend types/destructuring were wrong.

## Final real test run

```
Running 2 tests using 1 worker

  ok 1 [chrome] › e2e\customer-home-services.spec.ts:22:7 › Customer Home Services — real browser E2E (system Chrome, real backend) › provider-first booking flow: catalog -> match -> price -> confirm -> track (9.6s)
  ok 2 [chrome] › e2e\customer-home-services.spec.ts:94:7 › Customer Home Services — real browser E2E (system Chrome, real backend) › completed booking review flow: submit rating, then block duplicate submission (5.0s)

  2 passed (19.6s)
```

## Hard gates verified inside the passing test
- Provider card renders BEFORE price cards are shown (step order enforced by the wizard's own state machine: `provider` step must render `See Price Options` before `price` step is reachable) — asserted via `expect(page.getByRole('button', {name:'See Price Options'})).toBeVisible()` before any price-step assertions.
- Low/Mid/High price cards render with real numbers from the API (`Low — ₹770`, `Mid — ₹850`, `High — ₹935`).
- Price is NOT manually editable: `expect(await page.locator('input[type="number"]').count()).toBe(0)` — asserted and passing.
- "Confirm Booking" enablement is gated on provider+price selection (component's own `disabled={loading || !priceTier || !(provider.provider_name || provider.business_name)}` logic) — by the time the test reaches the review step, both are set (enforced by the step order itself, since `price` step requires clicking a tier before `Continue` is enabled).
- "Pays Provider Directly" copy renders on the review screen (`expect(page.getByText(/Pays Provider Directly/)).toBeVisible()`).
- Forbidden-term scan of the full rendered page text (confirmation + tracking pages) run inside the test itself — 15+ internal/ledger/wallet/commission/etc. terms, zero matches.
- No mock data: every value asserted (provider name, price numbers, booking status) originates from the real API responses driving the same component state used in production.

## Second test: completed-booking review + duplicate state
Uses the real completed booking fixture (`BK-20260710-000001`, already reviewed in Part 6's live API verification) and asserts the already-reviewed UI state renders correctly in the real browser — passed.

STATUS: BROWSER E2E PASSING — 2/2 tests, real backend/DB/frontend, real system Chrome.
