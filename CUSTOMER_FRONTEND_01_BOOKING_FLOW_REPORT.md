# CUSTOMER-FRONTEND-01 — Booking Flow Report

Implemented in `frontend/customer-app/app/customer/home-services/book/page.tsx` as a
single stateful component with steps: `service | details | location | provider | price | review | confirm`.

1. **Service** — category chips (from `/v1/catalog/master/categories`) then service
   chips (from `/v1/catalog/master/services?category_id=`). Requires login before
   proceeding (`isLoggedIn()` check redirects to `/login?next=...`). Calls
   `startBookingDraft(categorySlug, offeringSlug)` → real draft created.
2. **Details** — brand chips (if any exist for category), issue chips (if any exist
   for category+service), free-text issue description (required). Calls
   `updateDraftFields()`. Photo upload is explicitly disabled with an honest message
   rather than faked — no live backend endpoint accepts a raw file upload for this
   draft flow (only `/photos` which expects an already-hosted `photo_url`, and no
   media-upload endpoint was verified working in the time available).
3. **Location** — name/phone/zipcode/city/address1(required)/address2(optional).
   Calls `updateDraftFields()` then `checkServiceability()`. On `serviceable: false`,
   shows the exact required copy: "Service is not available in this area yet. Try a
   nearby zipcode or check again later." (backend's own message is shown when
   provided, falling back to this string).
4. **Provider (matching)** — on advancing past location, automatically calls
   `selectProviderForHomeService()` (`/match-and-price`). Loading state shows
   "Finding the best available provider near you...". No-provider state shows "No
   provider is available for this service in your area right now. Try a different
   time or check again later." Only customer-safe provider fields are rendered
   (see Customer Safety Report).
5. **Price** — renders Low/Mid/High cards from the match response's price options,
   Mid always shows "Recommended" badge, copy matches spec exactly ("Budget-friendly
   option" / "Recommended fair price" / "Higher acceptance priority"). Selecting a
   tier is client-side state only; the amount is never edited, only displayed as
   returned by the backend.
6. **Review** — shows service/issue/address/provider/selected price+amount/payment
   mode ("Customer Pays Provider Directly"). "Confirm Booking" CTA calls
   `confirmPriceChoice()` then `buildBookingSummary()` before allowing the final
   confirm (this happens transitioning from Price→Review, not on the Review step
   itself, since `/confirm-price-choice` must run before `/summary` is meaningful).
7. **Confirm** — calls `createCustomerHomeServiceBooking(draftId, idempotencyKey)`
   against the real `/confirm` endpoint with an `Idempotency-Key` header. Success
   copy matches spec exactly. Shows booking ID/number and a "Track Booking" button
   that routes to `/customer/bookings/{booking_id}`.

## HARD RULE enforcement
- The Price step button is `disabled` unless `priceTier` is set AND a provider
  object exists in `matchResult` (`!matchResult?.provider && !matchResult?.selected_provider`
  guard in `handlePriceNext`).
- The Review step's Confirm Booking action is only reachable after `confirm-price-choice`
  has succeeded, which itself requires the matched draft state server-side — the
  backend is the actual enforcement point; the frontend gate is a UX convenience,
  not the source of truth (correctly, since spec requires backend to be authoritative
  on price/provider values).

## Known gap
Live end-to-end testing hit `HOME_BOOKING_NO_PROVIDER_AVAILABLE` for the only
real seeded AC-installation + Ludhiana(141001) + Samsung combination available
in the dev DB, so the Price/Review/Confirm steps' real API responses were **not**
observed end-to-end with a live 200. See CUSTOMER_FRONTEND_01_LIVE_API_VERIFICATION_REPORT.md.
