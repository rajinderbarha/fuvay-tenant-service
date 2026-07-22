# Alternate Booking Route Audit

## Searched

`booking/router.py` (all 11 mutation routes), tenant/provider portal callers, customer routers,
admin routers, internal workers, lead-conversion modules (none found — no lead model exists in
this codebase), compatibility routers, `ServiceBooking` module (`final_records/models.py`),
`field_ops` routes, test/seed utilities.

## Findings

- **`Booking.convert_to_job`**: `SAME_BOOKING_SAME_CAPABILITY` as `create_booking`/
  `confirm_booking` in the sense that it operates on the same model, but a distinct capability
  (conversion, not creation/confirmation) — already correctly gated (`BOOKING_MANAGE`, now
  access-scope-aware, fixed this slice) and already derives `customer_id` from the Booking
  itself (no independent risk).
- **`cancel_booking`/`accept_reschedule`/`reject_reschedule`/`request_reschedule`**:
  `SAME_BOOKING_DISTINCT_CAPABILITY` — none of these can CREATE a Booking or advance it to a
  qualifying status; they operate on already-existing bookings and only move them toward
  cancellation/rescheduling. Not weaker alternates to creation/confirmation.
- **`add_note`** (`POST /v1/bookings/{id}/notes`): `WEAKER_ALTERNATE_ROUTE` **in a different
  sense** — it has zero persona/permission dependency at all (`get_current_user` only), the
  identical class of gap already fixed for `field_ops.router`'s own `add_note` in Slices
  2F-14A/C. However, it is NOT a weaker alternate for the create/confirm/convert capability this
  slice is scoped to — it cannot create a Booking, confirm one, or produce field_ops relationship
  evidence. Classified `OUT_OF_SCOPE_BLOCKS_MODULE_CLOSURE_ONLY_FOR_notes_CAPABILITY` — flagged
  as a follow-up candidate (product-decisions-required.md), not fixed this slice (mission's focus
  is explicitly "create_booking, confirm_booking, `_assert_tenant_customer_relationship`,
  `convert_to_job`" — notes is a distinct capability, same discipline applied throughout the
  2F-14 series for field_ops's own out-of-scope routes).
- **`ServiceBooking`** (`final_records` module): `DISTINCT_SERVICEBOOKING_PIPELINE` — inspected,
  confirmed entirely separate model/table, no shared code path with `Booking`, not modified.
- **`field_ops.create_job`**: already hardened (Slices 2F-14C-G), re-verified unchanged this
  slice (full regression, 165 tests passing).
- **Seed/test utilities**: re-confirmed (from Slice 2F-14G's own research) that no seed script
  constructs `Booking` or `Job` rows directly — no bypass found.

## Conclusion

No weaker LIVE route reaching the same create/confirm/convert capability was found beyond
`add_note` (which cannot reach that capability at all, so does not block THIS slice's closure).
`booking_preflight` is read-only (no persistence) and was correctly left unfixed as
out-of-scope (it cannot create evidence).
