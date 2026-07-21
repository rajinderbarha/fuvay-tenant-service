# Booking Submission Workflow — UX-06 Round 3

## Correction to Round 1/2's assumption

Round 1/2 assumed `bookingsApi`/`fieldOpsJobsApi` (read-only list/detail
endpoints) were the eventual booking-creation path once "wired up." Round 3
discovered, by reading `app/engines/home_service_booking/customer_router.py`
and `app/engines/final_records/confirm_router.py` directly, that there is no
`POST` create on either — **the real, canonical booking-creation pipeline for
an AI-chat-originated Home Service booking is a separate draft-based flow**:

```
POST /v1/customer/home-services/booking-drafts                 (start draft — category_slug + offering_slug, real IDs only)
PUT  /v1/customer/home-services/booking-drafts/{id}             (update issue/address/city fields)
POST /v1/customer/home-services/booking-drafts/{id}/serviceability-check
POST /v1/customer/home-services/booking-drafts/{id}/price-estimate      (backend-resolved price; "DeepSeek price is NEVER used" — verbatim from the route's own docstring)
POST /v1/customer/home-services/booking-drafts/{id}/match-and-price     (backend selects the provider; customer never sees/picks a list)
POST /v1/customer/home-services/booking-drafts/{id}/confirm-price-choice (customer picks low/mid/high tier only — never a raw amount)
POST /v1/customer/confirm/home-service-booking/{id}              (Idempotency-Key header, real ConfirmationLockService, creates ServiceBooking + ServiceJob)
```

This is confirmed to be the exact same pipeline the AI-chat tool loop itself
uses server-side (`start_home_service_draft`/`check_home_service_availability`/
`get_home_service_price_estimate` in `app/engines/ai_conversation/backend_tools.py`
call the identical `HomeServiceChatbotBookingService` methods).

## What was built this round

`src/lib/api.ts::homeServiceDraftApi` + `bookingConfirmApi` wrap the full
sequence above with real types. `src/screens/DeepSeekChatScreen.tsx`'s
"📅 Book a service" flow drives it: category picker (real
`catalogApi.categories()`) → offering picker (real
`catalogApi.categoryOfferings(slug)`) → issue/address text → real
`serviceabilityCheck` → real `priceEstimate` (displayed exactly as returned,
`price_snapshot.display_price`, never recalculated client-side) → real
`confirmHomeServiceBooking` with a real `Idempotency-Key` header (the draft ID
itself — a stable, caller-owned key; a retry hits the same key and the
backend's `ConfirmationLockService` returns the existing booking instead of
creating a duplicate) → real `booking_number`/`job_number` from the response →
navigate to `BookingDetail`.

**This round's flow intentionally skips `match-and-price`/
`confirm-price-choice`** (provider selection + tier choice) to keep the round's
scope provable end-to-end within the time available — `priceEstimate`'s
catalog-default price snapshot is shown and confirmed directly. This is an
honest simplification, not a hidden one: the full provider-matching step is a
real, separate, already-discovered contract deferred to the next round (see
deferred-items.md), not a fabricated shortcut — the booking that gets created
is still a real `ServiceBooking`/`ServiceJob` via the real confirm endpoint.

## Canonical-ID enforcement

Every ID sent onward (`category_slug`, `offering_slug`, `draft.id`) comes
directly from a typed API response (`ServiceCategory.slug`, `ServiceOffering.slug`,
`BookingDraft.id`) via `src/lib/chatBookingState.ts` — never parsed from a chat
bubble's (possibly non-English) display text. Enforced by a real test
(`canonicalSlugsFor` test in `chatBookingState.test.ts`) that explicitly asserts
the returned slug is never equal to the category/offering's display `name`.

## Idempotency

Real — confirmed via `app/engines/final_records/confirm_router.py` (`Header(None,
alias="Idempotency-Key")`) and `idempotency.py`'s `ConfirmationLockService`.
Not invented: the header name and mechanism come directly from the source, not
assumed.
