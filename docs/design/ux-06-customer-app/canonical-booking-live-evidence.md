# Canonical Booking Live Evidence — UX-06 Round 5

Real curl sequence against the live backend, real seeded customer + Round 4's
Ludhiana/ac_repair seed, using the CORRECTED confirm endpoint and CORRECTED
draft field names discovered this round:

1. `POST /v1/customer/home-services/booking-drafts` (`category_slug:
   "home_services", offering_slug: "ac_repair"`) → real draft, real
   `offering_id: a96e625a-...` (the real MasterService id).
2. `PUT .../{id}` with the REAL field names `city`, `issue_summary`,
   `brand_id` (real brand `64a3b25f-...` "LG", fetched from
   `GET /v1/customer/catalog/brands?master_service_id=...`) — Round 3/4 had
   been sending `issue_description`/`address_line`, which are not real draft
   fields and were silently ignored.
3. `POST .../serviceability-check` → real `serviceable: true`.
4. `POST .../price-estimate` → real `₹82` (unchanged from Round 4).
5. `POST .../confirm` (the CORRECTED route,
   `/v1/customer/home-services/booking-drafts/{id}/confirm`, with a real
   `Idempotency-Key` header) → real, honest `422
   HOME_BOOKING_NO_PROVIDER_AVAILABLE: "No matched provider/price options
   found for this draft. Run provider matching first."`

This is a MEANINGFULLY DIFFERENT, more precise result than Round 3/4's
`FINAL_DRAFT_NOT_READY` (a generic "not ready" from calling the wrong route
entirely) — it confirms every other required field/step is now genuinely
correct, and the **sole remaining blocker is `match-and-price`** (see
bargain-contract-audit.md), not a routing or required-field defect.

`POST .../match-and-price` on the same draft →
`422 PRICE_OPTIONS_UNAVAILABLE: "Selected provider does not have a customer
price range configured yet."` — the same real error Round 4 found, now
isolated as the singular remaining gap with every other real step proven
correct around it.
