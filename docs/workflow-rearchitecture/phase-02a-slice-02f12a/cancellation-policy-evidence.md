# Cancellation Policy Evidence — Slice 2F-12A (Workstream 3)

## Evidence gathered

### 1. Approved sibling `home_service_service.cancel_job` (Slice 2F-3B)
**Strength: EXPLICIT_PRODUCT_POLICY + TESTED_EXISTING_CONTRACT +
ESTABLISHED_CROSS_MODULE_PATTERN.**

`home_service_service.cancel_job` (the canonical ServiceJob execution
module, CLOSED and APPROVED in Slice 2F-3B) is the byte-for-byte
structural twin of `cancel_appointment`:
- Same signature shape: `cancel_job(db, job_id, tenant_id, user_id,
  reason, actor_role="provider", request_id=None)` — no `staff_member_id`
  parameter.
- Deliberately omits `_assert_staff_owns_job`, while every other job
  mutation (`accept`/`start`/`complete`/`diagnosis`/`work-note`/etc.)
  calls it — the identical asymmetry as coaching.
- Slice 2F-3B documented `POST /v1/provider/service-jobs/{job_id}/cancel`
  in `execution-assignment-enforcement-matrix.csv` and
  `execution-assignment-policy-matrix.csv` as **"Whole-job cancellation,
  tenant_owner/staff, ... n/a (tenant-wide provider action)"** — i.e.,
  explicitly business-wide, explicitly NOT assignment-scoped, and this
  was an APPROVED closure finding.

This directly proves the coaching `cancel_appointment` business-wide
behavior is the intentional, consistent, approved design across both
execution modules — not an oversight.

### 2. Signature evidence
**Strength: IMPLEMENTATION_ONLY (corroborating).**
`cancel_appointment` has no `staff_member_id` parameter at all — the
method was written to not receive the id needed for an assignment check,
matching `cancel_job`. The 7 assignment-checked methods all take
`staff_member_id` explicitly. This is a deliberate design difference, not
a forgotten line.

### 3. `actor_role="provider"` default
**Strength: IMPLEMENTATION_ONLY (corroborating).**
Both `cancel_appointment` and `cancel_job` default `actor_role="provider"`
(a generic provider-side actor), whereas the assignment-checked methods
hardcode `actor_role="staff"`. This reinforces that cancellation is
modeled as a provider-business action, not a coach-execution action.

### 4. Existing tests
**Strength: TESTED_EXISTING_CONTRACT.**
`test_sprint21_execution.py::TestCoachingExecution::test_cancel_happy`
calls `cancel_appointment(db, APPT_ID, TENANT_ID, USER_ID, reason=...)`
with a `USER_ID` that is not constrained to equal the appointment's
`staff_member_id` — and asserts success. The pre-existing test contract
already exercised (and depended on) the no-assignment-check behavior.

### 5. Frontend callers
**Strength: ABSENCE_OF_CHECK_ONLY (neutral).**
`coachingExecutionApi.cancel` exists but has no `.tsx` component caller.
Absence of a caller supports neither business-wide nor assigned-only more
than the other — it is neutral, and correctly does not drive the
decision.

### 6. Notification recipients
**Strength: NO_EVIDENCE.**
No notification infrastructure exists in `coaching_service` — so there is
no "who gets notified on cancel" signal to infer authority from.

## Overall classification
**ESTABLISHED_CROSS_MODULE_PATTERN + EXPLICIT_PRODUCT_POLICY** (via the
2F-3B-approved sibling). The evidence is consistent and non-contradictory
in favour of **business-wide cancellation for the authorized provider
persona (owner + canonical staff), tenant-scoped, not assignment-limited**.
Absence of `_assert_staff_owns_appt` is corroborated as intentional by
independent signature and cross-module evidence — it is not being treated
as proof on its own.
