# Known Limitations

1. No existing tenant/customer relationship is required for the pure manual creation mode — see
   manual-customer-authority.md. This is disclosed as a product-policy question, not silently
   assumed safe or silently fixed.
2. `booking_id`/`parent_job_id` concurrency race window remains (`CONCURRENCY_RISK_DOCUMENTED`,
   carried over from Slice 2F-14D, unchanged).
3. `address` is never derived from a referenced booking — remains independently client-supplied
   (product-decisions-required.md item 3).
4. Non-CONSULTATION→REPAIR parent/child combinations have no status eligibility gate — this is
   evidenced policy (`MULTIPLE_CHILDREN_ALLOWED`, no established restriction), not an oversight.
5. `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
   consolidation, booking/parent mutual-exclusivity formalization — all carried over from prior
   slices, unchanged.
