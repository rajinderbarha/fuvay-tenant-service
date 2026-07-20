# Known Limitations

1. First-time customers with no prior same-tenant Booking/Job cannot be manually assigned to a
   standalone Job — they must enter via the Booking flow first (see
   long-term-customer-directory-target.md). This is the ratified, intended behavior of the
   interim policy, not an oversight.
2. The relationship predicate counts ANY historical Booking/Job status as evidence (no filtering)
   — see tenant-customer-relationship-contract.md; this is evidence-based, not a gap, but is
   noted as a policy choice that could be revisited if product later wants a narrower definition.
3. `booking_id`/`parent_job_id` concurrency race window remains (`CONCURRENCY_RISK_DOCUMENTED`,
   carried over from Slice 2F-14D/14E, unchanged).
4. `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
   consolidation, `booking_id`/`parent_job_id` documented coexistence semantics, address
   derivation from booking — all carried over from prior slices, unchanged.
