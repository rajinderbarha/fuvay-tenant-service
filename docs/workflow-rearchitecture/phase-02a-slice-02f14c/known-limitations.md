# Known Limitations

1. `JobMedia`'s `media_id` field remains an opaque, unvalidated reference with no dedicated
   media-resolution service anywhere in this codebase — there is nothing to substitute a foreign
   reference into (no infrastructure exists that dereferences it), so this is not an active
   exploit path, but it is also not a validated reference in the traditional FK sense. Unchanged
   from Slice 2F-14A/14B's disclosure; no media infrastructure was built per explicit
   instruction.
2. `JobMedia` has no internal/customer-visible column — carried over, unchanged.
3. `create_job`'s `address` dict is not a normalized/validated reference — see
   product-decisions-required.md item 4.
4. `create_job`'s new FK validations add up to 3 additional DB round-trips
   (`service_type_id`/`parent_job_id`/`booking_id`/`customer_id` checks) when all four fields are
   supplied — a minor performance consideration, not a correctness or security concern; no
   batching/optimization was attempted this slice (out of scope, not requested).
5. A full independent re-verification of the ~170 non-field_ops rows in the master CSV remains
   out of scope for this slice (same disclosed limitation as Slices 2F-14A/14B).
