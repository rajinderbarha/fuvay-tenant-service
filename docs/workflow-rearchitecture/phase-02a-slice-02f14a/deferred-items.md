# Deferred Items

- `JobMedia` internal/customer-visible schema decision (product-decisions-required.md item 1).
- `respond_to_quote` non-customer `customer_id` design clarification (item 2).
- Legacy `Job.checklist`/`update_checklist` deprecation decision (item 3).
- Access-scope upgrade for `create_job`/`convert_to_repair`/`spawn_repair` (item 4).
- Router-level defense-in-depth dependency for quote-capability routes (item 5).
- A full independent re-verification of the non-field_ops 170 rows in
  `tenant-mutation-endpoint-inventory.csv` from a fresh runtime scan (out of scope — this slice
  corrected only the specific, concretely identified defects).
- Everything already deferred by Slice 2F-14 that remains out of scope: quotes/billing UI,
  offline sync, media/upload infrastructure, customer signature, PDF reports, supervisor/
  inspector/manager roles, migration 144, Admin/Tenant My Work, Next-Action aggregation, Booking
  Exception Resolution, `readonly@demo-ac-services.local` remediation.
- No second router module begun, per the mission's explicit instruction.
