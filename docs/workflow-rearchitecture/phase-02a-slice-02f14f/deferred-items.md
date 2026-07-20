# Deferred Items

- `TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING` (long-term target, explicitly out of
  scope).
- First-time manual customer onboarding / verified invitation or OTP flow.
- Whether relationship-status filtering should ever narrow beyond "any historical row"
  (product-decisions-required.md item 3).
- `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
  consolidation, `booking_id`/`parent_job_id` documented coexistence semantics, address
  derivation from booking, concurrency hardening — all carried over from prior slices, unchanged.
- No second router module begun, per the mission's explicit instruction.

With this slice, `create_job`'s individual-field ownership (2F-14C), cross-field relational
consistency (2F-14D), source eligibility/lineage (2F-14E), and manual customer authority (2F-14F)
are all closed at the security and domain-integrity level. Remaining open items are genuine
product-policy questions (the long-term directory capability and its dependents), not security
gaps.
