# Deferred Items

- Legacy vs. richer quote-surface consolidation decision (product-decisions-required.md item 1).
- `create_job`'s FK-validation hardening (item 2).
- `JobMedia` internal/customer-visible schema decision (carried over, unchanged).
- Legacy `Job.checklist`/`update_checklist` deprecation timing (carried over, unchanged).
- A full independent re-verification of the non-field_ops rows in the master CSV (out of scope,
  same as Slice 2F-14A).
- Everything already deferred by Slices 2F-14/2F-14A that remains out of scope: quotes/billing UI,
  offline sync, media/upload infrastructure, customer signature, PDF reports, supervisor/
  inspector/manager roles, migration 144, Admin/Tenant My Work, Next-Action aggregation, Booking
  Exception Resolution, `readonly@demo-ac-services.local` remediation.
- No second router module begun, per the mission's explicit instruction.
