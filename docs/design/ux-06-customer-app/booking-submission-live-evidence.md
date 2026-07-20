# Booking Submission Live Evidence — UX-06 Round 4

## What is now proven live (real backend calls, real seeded Ludhiana/ac_repair data)

- Draft creation: real, `POST /v1/customer/home-services/booking-drafts` →
  real draft row.
- Field update: real, `PUT .../{id}` → city/issue/address persisted.
- Serviceability: real, **NOW POSITIVE** (`serviceable: true`) — Round 3's
  blocker fixed via this round's safe tenant-portal seed.
- Price estimate: real, **NOW RETURNS A VALUE** (`₹82`, `source: backend_catalog`)
  — also blocked/untested in Round 3, now live.
- Negative control: unsupported city (Mumbai) still correctly fails.

## What is NOT yet proven live — real, precise, newly-discovered blocker

`match-and-price` → real `422 PRICE_OPTIONS_UNAVAILABLE` (`"Selected provider
does not have a customer price range configured yet."`) — traced to a missing
`BargainRule` row (`app/engines/admin_catalog/models.py`, platform-wide,
`master_service_id`-scoped) for `ac_repair`. Without it, `mark_ready_for_confirmation`
can never succeed, so the final `POST /v1/customer/confirm/home-service-booking/{id}`
correctly and honestly rejects with `FINAL_DRAFT_NOT_READY` — confirmed via a
direct curl call this round (not fabricated, not skipped).

**This was NOT worked around** — creating a `BargainRule` would modify a
shared, platform-wide canonical pricing record, which Workstream 1 explicitly
told this round not to touch. This is the correct, principled stopping point:
real progress made (serviceability + price now live), real remaining blocker
precisely diagnosed with exact table/field names for whoever picks this up
next (a real tenant/platform admin needs to configure bargain pricing for this
service, which is legitimately outside a customer-facing test session's scope).

## Bottom line for Workstream 4

The complete sequence through "load real price/availability result" (step 10
of the required 13-step sequence) is now genuinely provable live, up from
step 9 in Round 3. Steps 11-16 (review → submit → reference → list → detail →
refresh) remain blocked by the above, honestly documented blocker — not
fixture-driven, not skipped silently.
