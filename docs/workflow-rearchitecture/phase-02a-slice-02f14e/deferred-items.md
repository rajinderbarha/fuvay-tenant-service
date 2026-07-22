# Deferred Items

- Existing tenant/customer relationship requirement for manual creation
  (product-decisions-required.md item 1).
- Documented semantics for `booking_id` + `parent_job_id` coexistence, if ever needed (item 2).
- Address derivation from a referenced booking (item 3).
- Booking/parent concurrency hardening (item 4).
- Customer-consent recording, address normalization, tenant/customer directory design — not
  built, out of scope.
- `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
  consolidation — carried over, unchanged.
- No second router module begun, per the mission's explicit instruction.

With this slice, `create_job`'s individual-field ownership (2F-14C), cross-field relational
consistency (2F-14D), and source eligibility/lineage (2F-14E) are all closed at the security and
domain-integrity level. Remaining open items are genuine product-policy questions, not security
gaps.
