# Complaint Creation Linkage — Slice 2F-10 (Workstream 7)

## Record type used
`CreateComplaintIn.record_type` accepts any of `VALID_RECORD_TYPES`
(`app/engines/complaints/constants.py`): `service_booking`, `service_job`,
`service_invoice`, `coaching_appointment`, `real_estate_lead`,
`customer_review`. This confirms the complaint model attaches to
whichever of these distinct pipelines the customer references — it does
**not** merge Booking and ServiceBooking, nor Job and ServiceJob; each
`record_type` maps to its own FK column (`booking_id`, `job_id`,
`invoice_id`, `appointment_id`, `lead_id`, `review_id`) set by an
if/elif chain in `create_complaint`, one at a time, exactly matching the
supplied `record_type`.

## Tenant/provider derivation
`tenant_id` is resolved server-side from the linked record
(`_resolve_tenant_for_record`, unmodified) when not explicitly supplied —
a raw SQL `SELECT tenant_id FROM {table} WHERE id = :rid` keyed only off
`record_id`. The router itself never accepts a `tenant_id` field
(`CreateComplaintIn` has no such field) — there is no foreign-tenant
injection path to reject at the API boundary; it is structurally absent.

## Ownership fix (this slice)
Before this slice, **no check verified the customer owns the referenced
record at all** — `create_complaint` proceeded straight to persisting the
complaint regardless of who the record actually belonged to. Fixed by
calling the already-correct `ComplaintEligibilityService._fetch_record`/
`_customer_owns_record` (the same logic the separate, advisory
`check-eligible` endpoint has always used correctly) and rejecting with
`COMPLAINT_RECORD_NOT_FOUND` (missing record) or
`COMPLAINT_ACCESS_DENIED` (foreign record) before any `CustomerComplaint`
row is constructed.

## What was intentionally NOT added
`check_eligible`'s additional policy checks — record-status eligibility
window, complaint-window expiry, duplicate-open-complaint rejection — were
**not** wired into `create_complaint` this slice. `check-eligible` remains
the dedicated, separate advisory endpoint for that; enforcing those
additional policies at creation time as well would change existing
behavior beyond the conclusively-required ownership fix and constitutes a
product-policy decision (see `product-decisions-required.md`), not a
security defect.

## Duplicate complaint behavior
Not enforced at creation (unchanged) — `check_duplicate_open_complaint`
exists and is used only by the advisory `check-eligible` endpoint.
Customers can currently file multiple open complaints against the same
record; this is pre-existing, unmodified behavior, not a defect
introduced or discovered this slice.
