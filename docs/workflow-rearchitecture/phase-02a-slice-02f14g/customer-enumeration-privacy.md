# Customer Account Enumeration Privacy (Re-Verified Post-Tightening)

## Indistinguishable cases (all produce the identical `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED`, 422)

- Customer exists but has no qualifying tenant relationship (no Booking at all, or only
  non-qualifying-status Bookings, and no source-derived Job).
- Customer exists only in another tenant (with a fully qualifying, `CONFIRMED`-or-later
  relationship there) — the query never inspects rows outside the principal tenant.
- Customer has only non-qualifying draft/rejected/cancelled/expired/voided Booking records.
- Customer has only untrusted legacy/generic Job evidence (both `booking_id` and
  `parent_job_id` null).
- Customer has never appeared in the system at all (beyond passing the initial
  role=="customer"+active+non-deleted check).

All five produce the exact same code path and error — confirmed via source inspection: a single
`raise ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED", ...)` at the end of the
helper, reached whenever BOTH queries return no match, regardless of why.

## `FOREIGN_CUSTOMER` cases (unchanged, still uniform among themselves)

Invalid/disabled/deleted/wrong-role accounts continue to share the single `FOREIGN_CUSTOMER`
code (Slice 2F-14F) — not further distinguished this slice, since none of this slice's changes
touch that check.

## Conclusion

Tightening the predicate did not introduce any new distinguishable error path — the SQL-level
status/lineage filters simply change which rows the SAME two `select(...).limit(1)` queries can
match; the uniform-rejection contract is unaffected.
