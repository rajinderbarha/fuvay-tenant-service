# Product Decisions Required

1. **Whether an existing tenant-customer relationship should be required** for
   `PROVIDER_SELECTED_EXISTING_CUSTOMER` mode (any real customer account may currently be
   selected with no prior relationship check) — see customer-authority.md.
2. **Whether `booking_id`/`parent_job_id` should be formally mutually exclusive** on `create_job`
   — currently both may be supplied together and are independently cross-checked against their
   own customer, not against each other — see supported-creation-modes.md.
3. **Whether `Booking.status`/parent `Job.status` preconditions should be enforced on
   `create_job`'s manual reference fields** (e.g. requiring `BS.CONFIRMED` or
   `JS.QUOTE_APPROVED`) — currently not checked, since `create_job` is a generic manual endpoint,
   not the atomic conversion pipelines (`Booking.convert_to_job`/`convert_to_repair`) that already
   enforce these preconditions on their own dedicated routes.
4. **Concurrency hardening** for the booking/parent duplicate checks (`CONCURRENCY_RISK_DOCUMENTED`
   in duplicate-idempotency-policy.md) — would require a DB unique constraint or row locking
   pattern not currently established anywhere in this codebase for this scenario.
5. **Customer-consent recording for manual Job creation** — not built, out of scope.
6. **Address normalization** — not built, out of scope.
7. Carried over, unchanged: `JobMedia` internal/customer-visible schema; legacy checklist
   deprecation; legacy vs. richer quote-surface consolidation.
