# Deferred Items

- Booking/parent status preconditions on `create_job`'s reference fields (known-limitations.md
  item 1).
- Concurrency hardening for booking/parent duplicate checks (item 2).
- Formal mutual exclusivity of `booking_id`/`parent_job_id` (product-decisions-required.md item 2).
- Existing tenant-customer relationship requirement for manual customer selection
  (product-decisions-required.md item 1).
- Customer-consent recording, address normalization — not built, out of scope.
- `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
  consolidation — carried over, unchanged from prior slices.
- No second router module begun, per the mission's explicit instruction.

With this slice, `create_job`'s individual-field ownership (2F-14C) and cross-field relational
consistency (2F-14D) are both closed. No further field_ops job-creation integrity work remains
queued beyond the product decisions listed above.
