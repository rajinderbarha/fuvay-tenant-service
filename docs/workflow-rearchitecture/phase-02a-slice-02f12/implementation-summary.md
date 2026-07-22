# Slice 2F-12 Implementation Summary

## Scope
Complete authorization, ownership, and lifecycle closure for
`app.engines.execution.coaching_router` (4 sub-routers: `staff_router`,
`provider_router`, `customer_router`, `admin_router` — 12 mounted routes
total, 8 genuine mutations).

## Architecture finding
Fresh investigation confirmed `execution.coaching_router` operates on
`CoachingAppointment` (`app/engines/final_records/models.py`) — a
**CONFIRMED, already-booked appointment record** (post-confirmation
execution/CRM tracker: accept/reject/start/complete/no-show/reschedule/
cancel + notes). No slot-hold, capacity, or enrolment/conversion model
exists in this specific router. That machinery (`CoachingAppointmentDraft`,
`CoachingAppointmentSlotHold`, `CoachingAppointmentDraftEvent`) lives in a
**distinct module**, `app.engines.coaching_appointment` — inspected for
alternate-route classification, not implemented or modified (out of
scope). This mirrors exactly the architecture finding from Slice 2F-11
for real estate (same Sprint 21 author, same pattern, same module split
between pre-confirmation draft/slot logic and post-confirmation
execution).

## What was found
All 8 mutation routes (7 on `staff_router`, 1 on `provider_router`) used
`get_current_user` only — no role check at all. The only protection was
a pre-existing, correct **object-level** assignment check inside
`CoachingAppointmentExecutionService` (`_assert_staff_owns_appt`, exact
`staff_member_id` match) for 7 of the 8 mutations — `cancel_appointment`
(the `provider_cancel` route) does **not** call this assignment check at
all (confirmed by source read), meaning any authorized tenant staff/owner
— not only the assigned staff member — may cancel an appointment. This is
documented as an intentional business-level distinction (front-desk
cancellation), not a defect, consistent with the identical business-wide
vs. assignment-scoped distinction already established for real estate's
reads vs. mutations.

2 reads (`staff_timeline`, `provider_timeline`) and 1 customer read
(`customer_tracking`) were likewise `get_current_user`-only.
`admin_router`'s 1 route was already correctly `require_super_admin`-gated.

No technician/mobile caller was found anywhere for this module (confirmed
via repository-wide grep) — the same evidence gap already found and
closed for real estate. Unlike the real-estate slice (which needed a
2F-11A follow-up to correct an inconsistent read guard), this slice
applies the corrected, consistent standard from the outset: technician
is excluded from both the 8 mutations and the 2 staff/provider reads in
a single pass.

## What changed
1. **`app/engines/execution/coaching_router.py`**:
   - All 8 mutations now use `require_owner_or_office_staff_mutation`
     (role in {super_admin, tenant_owner, staff}, access-scope-aware) —
     technician excluded.
   - `staff_timeline`/`provider_timeline` now use a new local
     `require_owner_or_office_staff_read` (same persona set, no
     access-scope block — appropriate for a read), mirroring the
     identical fix applied to `execution.real_estate_router` in Slice
     2F-11A.
   - `customer_tracking` now uses `require_customer`.
   - `admin_router` is unchanged.
2. **New test file**: `tests/test_phase2f12_coaching_authorization.py`
   (31 tests) — role-gate HTTP tests for every sub-router persona,
   read-only-scope retention on reads, and re-verification of the
   pre-existing, unmodified per-appointment assignment ownership check
   (including the `cancel_appointment` non-assignment-limited finding).
3. **`docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`**
   — 8 rows updated from `UNVERIFIED` to `TENANT_MUTATION_ROLE_SCOPE_AWARE`.
4. **`docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`**
   — `app.engines.execution.coaching_router` row updated: 0/8 → 8/8
   protected.

## What did NOT change
`CoachingAppointmentExecutionService`'s existing, correct
`_assert_staff_owns_appt` assignment check, `APPT_TRANSITIONS` state
machine, and `_set_status`'s validate-before-mutate ordering were all
already correct and are unmodified. No permission or role was created.
No slot-hold/enrolment/conversion capability was built (none exists in
this router to build on). No frontend file was modified (no component
calls this module's API client at all). `app.engines.coaching_appointment`
was inspected but not modified. `field_ops.checklist_router`,
`field_ops.staff_router` were not begun. `readonly@demo-ac-services.local`
and migration 144 were untouched.

## Outcome
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` —
see `approval-gate.md`. Tenant mutation coverage: **125/182** (up from
117/182 — 8 newly protected, all within the pre-existing denominator;
this module's routes were already counted before this slice).
