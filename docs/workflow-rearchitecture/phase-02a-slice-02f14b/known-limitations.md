# Known Limitations

1. `add_note`/`add_media` remain tool-classified `AUTHENTICATED_ONLY_NO_PERMISSION_CHECK` despite
   a real, verified service-level fix (Slice 2F-14A) — not counted as protected in the canonical
   167/210 figure, consistent with that slice's own disclosure.
2. `create_job`'s foreign-key fields (`customer_id`, `booking_id`, `service_type_id`) are not
   validated against their source tables — pre-existing behavior, not a security gap, see
   product-decisions-required.md item 2.
3. The legacy `create_quote`/`respond_to_quote` surface and the richer `create_job_quote`/
   `send_job_quote`/`approve_job_quote`/`reject_job_quote` surface both operate on the same
   `JobQuote` table with no frontend caller for either — a design duality, not a security defect
   (see quote-model-lineage.md, product-decisions-required.md item 1).
4. `JobMedia` internal/customer-visible schema gap carried over from Slice 2F-14A, unchanged.
5. Legacy `Job.checklist`/`update_checklist` deprecation decision carried over from Slice 2F-14A,
   unchanged.
6. A full independent re-verification of the ~170 non-field_ops rows in the master CSV was not
   re-run from scratch this slice (same scope limitation disclosed in Slice 2F-14A).
