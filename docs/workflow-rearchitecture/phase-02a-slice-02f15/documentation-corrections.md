# Documentation Corrections to Slice 2F-14G

| File | Original claim | Correction |
|---|---|---|
| `phase-02a-slice-02f14g/approval-gate.md` | `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PROVENANCE_BLOCKED` — blocked specifically because "a tenant_owner can still self-confirm their own fabricated Booking... outside this slice's scope" | This slice (2F-15) closes exactly that residual gap by fixing `BookingService.create_booking` itself (the actual out-of-scope boundary named in 2F-14G). The provenance block is now resolved — see this slice's approval-gate.md for the corrected status. |
| `phase-02a-slice-02f14g/known-limitations.md` item 1 | "Closing this would require modifying `BookingService.create_booking`/`confirm_booking`... outside this slice's scope" | Confirmed and acted upon in Slice 2F-15 — `create_booking` was modified (customer validation + relationship requirement); `confirm_booking` itself did NOT need modification (its existing tenant-ownership/state checks were already correct — the fix belongs entirely upstream, at creation). |
| `phase-02a-slice-02f14g/relationship-evidence-threat-model.md` | Documented the exploitable bootstrap chain as a residual, disclosed risk | Confirmed exploitable via this slice's own `test_bootstrap_attack_no_relationship_rejected` (which reproduces the exact chain and proves it now fails at booking-creation) — the threat model's own description was accurate; only its "not fixed" status is superseded. |

Preserved, unchanged: `field_ops.router` 28/28, `field_ops.staff_router` 6/6, field_ops subtotal
40/40, `_assert_tenant_customer_relationship`'s own predicate (unmodified this slice — the fix is
entirely upstream in the booking engine), `Booking.convert_to_job` (unmodified), Booking/
ServiceBooking separation, `field_ops.Job`/ServiceJob separation, ServiceJob-only PartsRequest
ownership, `quote_checklist` separation — none of these were altered this slice.

No file was deleted. A superseded notice is added to
`phase-02a-slice-02f14g/approval-gate.md` per the established pattern.
