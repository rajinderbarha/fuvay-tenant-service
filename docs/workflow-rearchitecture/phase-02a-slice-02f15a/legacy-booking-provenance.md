# Legacy Booking Provenance

## The risk
Slice 2F-15 closed `create_booking`'s customer-validation and relationship-requirement gaps for NEW tenant-assisted bookings, but explicitly disclosed (2F-14G/2F-15) an unresolved residual risk: any Booking already sitting in a qualifying status (`CONFIRMED` or later) — regardless of WHO or WHAT created it, including bookings created before this slice's own validation existed, or via any as-yet-unaudited path — was treated as sufficient evidence of a genuine tenant-customer relationship. This meant:

1. A provider could create an assisted Booking, immediately confirm it, and use that Booking as "evidence" to create ANOTHER assisted booking for the same fabricated customer relationship (self-bootstrapping chain).
2. A legacy Booking row that predates any of these checks (created via a path this whole initiative has not audited) could silently carry the same authority.

## The fix — no new column, no migration
`BookingStatusHistory` is written on every Booking status transition, including the very first one at creation (`from_status IS NULL`), and it already carries `changed_by_role` — the role of whoever performed that transition. This column existed before this slice and needed no schema change.

Both relationship-evidence queries (`FieldOpsService._assert_tenant_customer_relationship` and `BookingService.create_booking`'s own check) now additionally require the qualifying Booking's own creation-history row (`from_status IS NULL`) to show `changed_by_role == "customer"`. A provider-created Booking — however confirmed, however old — can no longer, by itself, establish relationship authority.

## What this means for genuinely legacy rows
Any Booking created by a real customer (`changed_by_role == "customer"` at creation) — including ones created long before this slice, or before 2F-15's own validation existed — is UNAFFECTED and continues to serve as valid relationship evidence. Only provider/tenant-created rows lose default trust; this is the correct direction for the risk being closed (a provider cannot fabricate a customer relationship by creating and confirming a booking on the customer's behalf without independent proof).

## What remains genuinely out of scope
This slice does not audit or re-classify any Booking rows already in the database, does not add a migration or provenance column, and does not attempt to retroactively distinguish "trustworthy legacy data" from "untrustworthy legacy data" by any means other than the creation-time `changed_by_role` value that already existed. If a real customer never interacted with the system before a provider-created Booking (e.g. phone-order booking with no app account), that Booking's true trustworthiness is a business/product question this slice cannot resolve — see `product-decisions-required.md`.
