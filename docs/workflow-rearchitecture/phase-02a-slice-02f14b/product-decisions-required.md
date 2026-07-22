# Product Decisions Required

1. **Legacy `create_quote`/`respond_to_quote` vs. richer `create_job_quote`/`send_job_quote`/
   `approve_job_quote`/`reject_job_quote` duality.** Both surfaces write the same `JobQuote`
   table with overlapping but not identical semantics (`status="pending"` vs `"draft"`/`"sent"`
   initial states). No frontend caller exists for either surface (frontend-internal-caller-audit.md).
   Product should decide whether to consolidate to one surface or formally document both as
   supported.
2. **`create_job`'s `customer_id`/`booking_id`/`service_type_id` foreign references.** None of
   these are FK-validated against other tables in this codebase (pre-existing, unchanged this
   slice). Whether to add referential validation is a data-integrity hardening question, not a
   security gap (no privilege escalation results from an invalid reference — it only affects the
   created Job's own data quality).
3. **`JobMedia` internal/customer-visible schema decision** (carried over from Slice 2F-14A,
   unchanged, still open).
4. **Legacy `Job.checklist`/`update_checklist` deprecation timing** (carried over from Slice
   2F-14A, unchanged, still open).
