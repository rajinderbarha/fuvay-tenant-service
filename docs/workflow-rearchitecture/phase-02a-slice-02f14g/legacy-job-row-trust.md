# Legacy Job-Row Trust

## Disposition: SOURCE_DERIVED_JOB_ROWS_ONLY

## Investigation

Existing `field_ops.Job` rows CAN be reliably distinguished into two buckets using only
existing fields:

1. **Source-derived** (`booking_id IS NOT NULL` or `parent_job_id IS NOT NULL`) — structurally
   created via `Booking.convert_to_job`, `convert_to_repair`, `spawn_repair_from_consultation`,
   or `create_job`'s own booking/parent modes. Every one of these paths derives `customer_id`
   from an already-validated source record (the Booking or parent Job) — the customer_id was
   never independently client-chosen for these rows, regardless of when they were created
   (before or after Slices 2F-14C–F).
2. **Generic/standalone** (`booking_id IS NULL AND parent_job_id IS NULL`) — created via
   `create_job`'s standalone manual mode. **No field distinguishes a row created after Slice
   2F-14F's hardening (customer_id validated against the User table + relationship-checked) from
   one created before any of Slices 2F-14C–F existed (customer_id accepted with zero
   validation).**

`Job.source` (a pre-existing field, default `"direct"`) was checked as a possible distinguisher:
only `Booking.convert_to_job` explicitly sets it (`source="booking"`) — every other creation path
(including hardened and pre-hardening standalone `create_job`, plus `convert_to_repair`/
`spawn_repair`) leaves it at the default `"direct"`. It does not distinguish hardened from
unhardened standalone rows.

`created_at`, `created_by`, and audit/status-history records were also checked: `JobStatusHistory`
records the transition but not a "was this customer_id independently validated at creation"
marker — no such marker was ever recorded, and inventing one now (a deployment-timestamp cutoff)
is explicitly forbidden by this slice's mission ("do not invent a deployment timestamp or source
marker").

## Conclusion

Per the mission's explicit instruction ("if trustworthy legacy provenance cannot be established,
exclude generic Job rows from relationship evidence rather than grandfathering them silently"),
**generic/standalone Job rows are now excluded from `_assert_tenant_customer_relationship`'s Job
query entirely** — only `booking_id`-or-`parent_job_id`-derived rows qualify.

## Why this does not break legitimate use

Any generic Job row that was legitimately created via the hardened post-2F-14F standalone path
could only have been created because SOME qualifying evidence (a Booking or another
source-derived Job) already existed for that customer at that time. Excluding the generic Job
itself from being usable as *further* evidence does not remove that original qualifying evidence
— it remains queryable independently. No legitimate relationship is lost by this exclusion.
