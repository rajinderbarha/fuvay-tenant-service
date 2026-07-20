# Approval Gate — Slice 2F-12A

## Status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## The question and its resolution
Slice 2F-12 left one question unresolved: `cancel_appointment` omits the
`_assert_staff_owns_appt` assignment check the other 7 mutations use.
This slice adjudicates it as **business-wide cancellation, VERIFIED** via
approved cross-module evidence — no code change needed.

## Reasoning

### ROUTER_SECURITY_CLOSED: YES
All 8 route guards remain intact (`require_owner_or_office_staff_mutation`
on the 8 mutations, `require_owner_or_office_staff_read` on the 2
provider/staff reads, `require_customer` on customer tracking,
`require_super_admin` on admin) — unmodified, re-verified. Read-only
mutation scope is denied. Wrong personas (technician/customer/guest/
unknown) are denied. Directly tested in
`direct-cancellation-authorization-tests.csv`.

### CANCELLATION_OBJECT_AUTHORIZATION_CLOSED: YES
- **Tenant-owner**: business-wide (`TENANT_OWNER_BUSINESS_WIDE_CANCEL`) —
  explicit.
- **Canonical staff**: business-wide (`STAFF_BUSINESS_WIDE_CANCEL`) —
  explicit, verified via the approved 2F-3B sibling `cancel_job`
  ("tenant-wide provider action").
- **Assignment requirements**: none for cancel (deliberate) — proven
  intentional by the identical, approved sibling pattern, the signature
  evidence (no `staff_member_id` parameter), and the pre-existing test
  contract. Applying `_assert_staff_owns_appt` mechanically would wrongly
  block tenant_owner and super_admin (see `appointment-assignment-model.md`).
- **Super-admin**: existing business-wide behavior preserved.
- **Technician / customer**: denied (`TECHNICIAN_CANCEL_DENIED` /
  `CUSTOMER_CANCEL_DENIED`) — technician exclusion is actually stricter
  than the approved sibling.
- **Cross-tenant**: denied (tenant filter), no mutation.
- **Same-tenant unauthorized**: there is no "unauthorized same-tenant
  office persona" for cancellation — business-wide IS the verified policy;
  the only same-tenant actors are owner/staff, both authorized.
- Direct tests prove the matrix (`test_phase2f12a_coaching_cancellation.py`,
  27 tests).

### CANCELLATION_STATE_INTEGRITY_CLOSED: YES
Legal cancel source states (`confirmed`/`accepted`/`scheduled`) are
explicit; final/in-progress states (`started`/`completed`/`no_show`/
`rejected`/`cancelled`) are protected (`_assert_transition` before any
mutation); repeated cancellation is rejected (empty transition set);
invalid and denied attempts create no mutation, no audit event, no
notification — all directly tested (`cancellation-state-matrix.csv`).

### PRIVACY_CLOSED: YES
Slice 2F-12 privacy findings intact. Cancellation reason handling creates
no new PII exposure — the reason is visible only to the appointment's own
customer (via `customer_tracking`'s `failure_reason`, ownership-filtered)
and the tenant's own staff; no notification broadcasts it
(`cancellation-reason-integrity.md`, `cancellation-audit-notification.md`).

### ALTERNATE_ROUTE_CLOSED: YES
The only route cancelling a confirmed `CoachingAppointment` is
`provider_cancel` (this router). `coaching_appointment.cancel_draft`
reaches a distinct model (`CoachingAppointmentDraft`, customer-owned) —
not a weaker alternate to the same record (`alternate-cancellation-route-audit.md`).

### DOMAIN_INTEGRITY_CLOSED: YES
Slice 2F-12 lifecycle findings intact and unmodified.

### PRODUCT_POLICY_CLOSED: BLOCKED
Cancellation authority is now CLOSED (verified), removed from the open
list. The residual BLOCKED items are unrelated carryovers (note-visibility
granularity, `coaching_appointment` architecture, future technician
participation, coarse audit-role label) — none block security, integrity,
or privacy closure. See `product-decisions-required.md`.

## Final combined status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

Cancellation object authority is verified, not blocked — the mission's
prohibition ("do not claim complete security closure while same-tenant
staff cancellation authority remains unverified") is satisfied: it is now
verified.

## Quality gates (44) — summary
All satisfied and verified directly. Evidence distributed across the
other 19 files in this directory.

## Global coverage
Unchanged: **125/182**. This slice made no source or classification
change (`global-coverage-confirmation.md`).

## Stop condition honored
No source file was changed (verify-and-document slice) — only a new test
file and documentation (this slice's own + 2F-12 corrections).
`cancel_appointment`, `APPT_TRANSITIONS`, the 7 assignment checks, all 8
guards, reads, customer tracking, and `app.engines.coaching_appointment`
are unmodified. No permission or role was created. No financial workflow,
no booking-pipeline merge. `field_ops.checklist_router`/`field_ops.staff_router`
were not begun. `readonly@demo-ac-services.local` and migration 144 were
untouched. No visual redesign. **Stopping here per instruction — not
beginning another module.**
