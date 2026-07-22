# Deferred Items

- `JobMedia` internal/customer-visible schema decision (carried over, unchanged).
- Legacy `Job.checklist`/`update_checklist` deprecation timing (carried over, unchanged).
- Legacy vs. richer quote-surface consolidation (carried over, unchanged).
- `create_job`'s `address` dict normalization (product-decisions-required.md item 4).
- A full independent re-verification of the non-field_ops rows in the master CSV (out of scope,
  same as Slices 2F-14A/14B).
- Everything already deferred by Slices 2F-14/2F-14A/2F-14B that remains out of scope: media/
  upload infrastructure, customer signature, PDF reports, supervisor/inspector/manager roles,
  migration 144, Admin/Tenant My Work, Next-Action aggregation, Booking Exception Resolution,
  `readonly@demo-ac-services.local` remediation.
- No second router module begun, per the mission's explicit instruction.

With this slice, `field_ops.router` and `field_ops.staff_router` are both fully closed at the
route-authorization level (28/28 and 6/6 respectively). No further field_ops mutation-enforcement
work remains queued.
