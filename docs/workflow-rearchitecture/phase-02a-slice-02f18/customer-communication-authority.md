# Customer Communication Authority

## Authoritative relationship
A provider/staff user may only open (or send into) a chat thread tied to a
`record_id` that resolves to a `ServiceBooking`, `ServiceJob`, or
`CustomerComplaint` belonging to their OWN tenant — enforced this slice in
`ChatThreadService.create_thread` (see `implementation-summary.md` finding
3). Before this fix, the caller's own `tenant_id` was trusted outright and
the resolved record's actual tenant was never compared against it.

- Booking/ServiceBooking are NOT adapted into each other — `_resolve_record_parties`
  only recognizes `record_type in ("service_booking", "service_job")`
  against `app.engines.final_records.models.ServiceBooking`/`ServiceJob`
  specifically; the legacy `Booking` model and `field_ops.Job` are never
  touched by this resolution path.
- The customer identity on a thread (`ChatThread.customer_id`) is derived
  from the resolved record (`booking.customer_id`), not from a
  client-supplied value, for the provider-initiated path. For the
  customer-initiated path (`customer_router.py`), the caller's own
  `customer_id` (`uuid.UUID(u.user_id)`, JWT-derived) is compared against
  the resolved record's `customer_id` and rejected on mismatch (finding 3).
- Provider-internal content vs. customer-visible content is separated by
  the (now-enforced) `visibility` field — see
  `content-visibility-classification.csv`.

## No tenant-customer directory
This module was NOT extended with any lookup that lets a tenant browse or
search arbitrary customers — the only way a provider/staff user reaches a
customer conversation is via a pre-existing linked record they already have
legitimate access to elsewhere in the platform (booking/job/complaint
detail pages), consistent with the OUT OF SCOPE constraint against building
a tenant-customer directory.
