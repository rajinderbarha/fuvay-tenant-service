# Product Decisions Required

1. **`booking/router.py`'s `add_note` route has zero persona/permission dependency** — same
   class of gap already fixed for `field_ops.router` in Slices 2F-14A/C. Whether/when to apply
   the identical fix to the booking engine's notes capability is a scoping decision for a future
   slice (not part of this slice's create/confirm/convert focus).
2. **`cancel_booking`/`accept_reschedule`/`reject_reschedule`/`request_reschedule` remain
   `PERMISSION_ONLY_NOT_SCOPE_AWARE`** — whether to extend the `require_tenant_mutation_permission`
   upgrade to these distinct capabilities is a scoping decision, not a proven same-record bypass
   of anything fixed this slice.
3. **Legacy pre-fix Bookings**: any `Booking` created via the (now-closed) unvalidated
   tenant-assisted path before this slice's deployment could theoretically still exist in a
   qualifying status with no genuine relationship. Whether to audit/remediate existing data is a
   product/ops decision — no migration or data audit was performed this slice (see
   qualifying-relationship-provenance.md).
4. **Tenant-local customer directory / verified invitation workflow** (long-term target, carried
   over from Slice 2F-14F/G, unchanged).
5. **Cancelled/voided Booking disambiguation via `BookingStatusHistory`** (carried over from
   Slice 2F-14G, unchanged).
