# Known Limitations

1. `Booking.status`/parent `Job.status` are not preconditioned on `create_job`'s manual
   booking_id/parent_job_id references (see product-decisions-required.md item 3) — a booking in
   `draft` status, or a consultation not yet in `QUOTE_APPROVED`, could still be referenced by a
   manually-created Job via `create_job`. This is distinct from the atomic conversion pipelines
   (`Booking.convert_to_job`, `convert_to_repair`), which DO enforce these preconditions on their
   own separate routes — `create_job`'s reference fields were never intended to replace those
   pipelines, and no evidence exists that any caller relies on a status precondition here.
2. Concurrent creation from the same `booking_id`/consultation `parent_job_id` has a documented,
   pre-existing race-condition class (`CONCURRENCY_RISK_DOCUMENTED`) shared with
   `Booking.convert_to_job`/`convert_to_repair` themselves — not newly introduced, not fixed this
   slice (no DB-level locking pattern exists elsewhere in this codebase to reuse; would require a
   migration, out of scope unless already an approved pattern).
3. `booking_id`/`parent_job_id` are not mutually exclusive — both may be supplied together; each
   is independently cross-checked against its own customer/service, not against each other (see
   product-decisions-required.md item 2).
4. `service_type_id` accepting an empty string bypasses ownership validation entirely (carried
   over from Slice 2F-14C, unchanged) — the field is still technically REQUIRED by the request
   contract (`data["title"]`/`data["service_type_id"]`, no `.get()`), so this is a corner case of
   the validation's truthiness check, not a bypass of a mandatory field.
5. `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
   consolidation — all carried over, unchanged.
