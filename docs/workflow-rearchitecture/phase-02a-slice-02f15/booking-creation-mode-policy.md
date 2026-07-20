# Booking Creation Mode Policy (Post-Implementation)

## CUSTOMER_SELF_SERVICE_BOOKING

- **Initiator**: authenticated `customer`.
- **Authoritative tenant**: server-resolved via serviceability matching.
- **Authoritative customer**: server-derived from `u.user_id` — never client-suppliable.
- **Authoritative service**: server-resolved from `service_id` via `ServiceabilityService`.
- **Required relationship**: none — this IS the legitimate first-contact path.
- **Allowed initial status**: `BS.PENDING_CONFIRMATION`.
- **Required confirmation actor**: `tenant_owner` (separate call).
- **Qualifies as field_ops relationship evidence**: only once `CONFIRMED` (or later).
- **Alternate route**: none.

## EXISTING_CUSTOMER_ASSISTED_BOOKING (fixed this slice; was previously `UNVERIFIED_PROVIDER_DRAFT`)

- **Initiator**: `tenant_owner` supplying `customer_id` in the request body.
- **Authoritative tenant**: server-resolved via serviceability matching (same mechanism as
  self-booking).
- **Authoritative customer**: the supplied `customer_id`, now validated (existence + canonical
  `customer` role + active + non-deleted) AND required to already have an existing same-tenant
  relationship (a qualifying-status Booking or a source-derived Job) — **fixed this slice**.
- **Authoritative service**: same as self-booking.
- **Required relationship**: **YES, now enforced** — this is the core fix. Previously `NONE`
  (confirmed exploitable, Slice 2F-14G).
- **Allowed initial status**: `BS.PENDING_CONFIRMATION`.
- **Required confirmation actor**: `tenant_owner` (may be the same actor who created it).
- **Qualifies as field_ops relationship evidence**: only once `CONFIRMED` (or later) — same rule
  as self-booking, unchanged.
- **Alternate route**: none found.

## VERIFIED_OFFLINE_CUSTOMER_BOOKING / SYSTEM_DERIVED_TRUSTED_BOOKING / LEGACY_BOOKING

No evidence of a distinct route or mode for these — the two modes above (`CUSTOMER_SELF_SERVICE_BOOKING`
and `EXISTING_CUSTOMER_ASSISTED_BOOKING`) are the only two the single `POST /v1/bookings` endpoint
supports, disambiguated purely by `u.role`. No separate "verified offline booking" capability or
"system/internal booking creation" caller exists anywhere in this codebase (confirmed: `Job(`
construction sites and `Booking(` construction sites were both exhaustively searched in Slice
2F-14G's research and this slice's follow-up — only the one `Booking(...)` constructor exists, in
`create_booking` itself).

## No route ambiguously represents multiple modes through an untrusted customer_id

Confirmed: the single route disambiguates cleanly by `u.role == "customer"` vs. not — there is no
code path where an untrusted `customer_id` reaches persistence without now passing through either
the server-derivation branch (self-booking) or the validation+relationship-check branch (assisted
booking, fixed this slice).
