# Cancellation Audit & Notification — Slice 2F-12A (Workstream 9)

## Audit event
- **Event name**: `CA_EV_CANCELLED` (`"appointment_cancelled"`), written
  as a `CoachingAppointmentExecutionEvent` row by `_set_status`.
- **Actor identity**: `actor_user_id = user.user_id` — the **actual**
  authenticated user performing the cancellation (correct, not
  fabricated).
- **`actor_role`**: `"provider"` — a coarse provider-side label
  (hardcoded default), identical to the approved sibling `cancel_job`.
  The actor *user* is exact; the *role* label is a deliberately generic
  "provider" (both tenant_owner and staff are provider-side personas).
  Not a defect — matches the established cross-module pattern; changing
  it to the granular role would be a non-required audit-schema change.
- **Tenant ID**: `appt.tenant_id` (from the tenant-verified appointment).
- **Appointment ID**: `appt.id`.
- **Previous → result status**: `old_status` → `cancelled` (both recorded
  on the event).
- **Reason handling**: stored as the event `notes` and
  `appt.failure_reason`.

## Notification
- **None** — `coaching_service` has no notification infrastructure at all
  (confirmed by grep for `notify`/`notification`). No customer, assigned
  staff, or tenant-owner notification is sent on cancellation. This is a
  pre-existing module characteristic (same as documented in Slice 2F-12),
  not built or removed this slice.

## Requirements verified
- **Denied cancellation produces no success audit event**: the guard
  (`require_owner_or_office_staff_mutation`) rejects denied personas
  before the service is reached — no event row is created. For
  invalid-state cancels, `_assert_transition` raises before the event
  row is constructed (`_set_status` writes the event only after the
  transition check passes) — proven by
  `test_illegal_source_states_rejected_no_mutation` (`db.add` never
  called).
- **Invalid-state cancellation produces no success notification**:
  trivially true (no notification exists at all).
- **Cross-tenant attempt produces no information leak**: `_get_appt`'s
  tenant filter returns not-found — no event, no data returned.
- **Audit actor reflects the actual owner/staff member**: `actor_user_id`
  is the real user.
- **Cancellation does not fabricate customer consent**: the event
  attributes the action to `actor_role="provider"`, not the customer —
  no customer-consent field is set.

## No infrastructure built
Per the mission's instruction, no notification infrastructure was created.
