# Approval Gate — Slice 2F-12

## Status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Architecture finding (load-bearing for this whole gate)
Fresh investigation confirmed `app.engines.execution.coaching_router`
operates on `CoachingAppointment` — a CONFIRMED, already-booked
appointment (execution/CRM tracker: accept/reject/start/complete/
no-show/reschedule/cancel + notes), not a learning-management system,
course-commerce platform, or slot-hold/enrolment marketplace. No such
model exists in this router's reach. The pre-confirmation slot-hold/
draft machinery lives in a distinct module, `app.engines.coaching_appointment`
(inspected, not modified) — the exact same architectural split already
established for real estate (Slice 2F-11).

## Reasoning

### SECURITY_CLOSED: YES (ROUTER-LEVEL) — object authority of cancel verified in 2F-12A
**[CORRECTION]** At 2F-12 time this was labeled a full SECURITY_CLOSED
without having verified `cancel_appointment`'s same-tenant staff object
authority (only its router guard and tenant ownership were proven). That
object-authority question is now resolved in Slice 2F-12A (business-wide,
verified via the approved 2F-3B sibling pattern) — so the closure is now
genuinely complete, but the 2F-12 claim was ahead of its evidence for
this one route. The router-level facts below remain accurate.

All 8 mounted mutations (7 on `staff_router`, 1 on `provider_router`) —
previously **`get_current_user`-only, no role check at all** — now
require `require_owner_or_office_staff_mutation` (role in {super_admin,
tenant_owner, staff}, access-scope-aware; technician excluded per direct
evidence that no mobile/technician client has ever called this module).
The pre-existing, correct per-appointment `_assert_staff_owns_appt`
assignment check (7 of 8 mutations) is unmodified and re-verified.
`cancel_appointment`'s non-assignment-limited design was documented here
as "plausibly intentional business-wide" but was left **UNVERIFIED** by
this slice. **[VERIFIED IN SLICE 2F-12A]** — the identical, approved
sibling `home_service_service.cancel_job` (Slice 2F-3B, documented as a
"tenant-wide provider action") proves business-wide cancellation is the
intentional, cross-module-consistent design; cancellation object
authority is now CLOSED, not merely documented. See
`phase-02a-slice-02f12a/approval-gate.md`. 3 read routes were also fixed
from `get_current_user`-only to role-appropriate guards
(`require_owner_or_office_staff_read`/`require_customer`) — applied from
the outset with the corrected, consistent standard (no follow-up slice
needed, unlike real estate's 2F-11→2F-11A split). `admin_router`'s 1
route was already correctly `require_super_admin`-gated, unmodified. No
weaker alternate route exists (`alternate-coaching-route-audit.md`).
Zero unverified routes remain — runtime inventory confirms 8/8 mutation
routes verified.

### DOMAIN_INTEGRITY_CLOSED: YES
The `APPT_TRANSITIONS` state machine and `_set_status`'s
validate-before-mutate ordering were already correct — re-verified,
unmodified. Final states (`completed`, `no_show`, `rejected`,
`cancelled`) are protected (empty transition sets). No confirmed
integrity defect was found. Every capability the mission anticipated for
slot-hold/capacity/enrolment/conversion domains is confirmed absent, not
silently broken — there is nothing to fail integrity closure on for
capabilities that don't exist in this router.

### PRIVACY_CLOSED: YES
Tenant/customer isolation is enforced (tenant filter in `_get_appt`;
customer_id filter in `customer_tracking`'s inline query; customer-visible
note filtering in `get_notes`). No proven PII leak was found. Technician
is excluded from all reads and mutations alike, from the outset.

### PRODUCT_POLICY_CLOSED: BLOCKED
A small number of genuine, non-security product questions remain open
(whether `cancel_appointment` should be assignment-limited, note-
visibility permission granularity, `coaching_appointment`'s own
architecture) — see `product-decisions-required.md`. None of these block
security, domain-integrity, or privacy closure.

## Final combined status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## Quality gates (57) — summary
All satisfied **except** the full object-level verification of
`cancel_appointment`'s same-tenant staff authority, which this slice
labeled satisfied but had in fact left UNVERIFIED (only the router guard
and tenant ownership were proven for cancel). That single gate is now
genuinely closed by Slice 2F-12A (business-wide, verified via the
approved 2F-3B cross-module pattern) — see
`phase-02a-slice-02f12a/approval-gate.md`. Gates targeting nonexistent
capabilities (slot-hold/capacity/enrolment/conversion) are satisfied
vacuously and honestly, per direct confirmation of absence, not
fabricated evidence. Evidence distributed across the other 26 files in
this directory.

## Global coverage
Tenant mutation coverage: **125/182** (up from 117/182 — 8 newly
protected, all within the pre-existing denominator; this module's routes
were already counted before this slice). Customer route coverage
unaffected (this module's one customer route is a read, not a mutation,
and was never part of the denominator).

## Stop condition honored
Only `app/engines/execution/coaching_router.py` (dependency swaps + 1
new local helper function) was modified for behavior, plus the 2
global-coverage CSVs. No other file under `app/engines/execution/` or
`app/engines/complaints/` was touched. `field_ops.checklist_router`,
`field_ops.staff_router`, and `app.engines.coaching_appointment` were not
begun or modified. No permission, role, or financial workflow was
created. No booking-pipeline merge occurred. No frontend file was
modified. `readonly@demo-ac-services.local` and migration 144 were
untouched. No visual redesign occurred. **Stopping here per instruction —
not beginning another router module.**
