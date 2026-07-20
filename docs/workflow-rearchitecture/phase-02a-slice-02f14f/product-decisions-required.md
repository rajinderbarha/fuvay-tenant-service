# Product Decisions Required

1. **`TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING`** (the long-term target) — see
   long-term-customer-directory-target.md. Explicitly out of scope this slice.
2. **First-time manual customer onboarding** — under the ratified interim policy, a tenant cannot
   manually create a Job for a customer with zero prior same-tenant Booking/Job; such customers
   must enter through the Booking flow first. Whether/how to build a verified first-contact path
   (invitation, OTP, etc.) is deferred to the long-term directory capability.
3. **Whether relationship status should ever be filtered** (e.g. excluding very old or
   test-looking records) — currently `ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP` (any status
   counts), since no schema-level distinction exists to filter on (see
   tenant-customer-relationship-contract.md).
4. Carried over, unchanged: `JobMedia` internal/customer-visible schema; legacy checklist
   deprecation; legacy quote-surface consolidation; `booking_id`/`parent_job_id` documented
   coexistence semantics (if ever needed); address derivation from booking; concurrency
   hardening.
