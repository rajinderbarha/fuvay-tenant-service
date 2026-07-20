# Cancellation Route Reconciliation — Slice 2F-12A (Workstream 1)

## `cancel_appointment` full trace
- **HTTP method / path**: `POST /v1/provider/coaching-appointments/{appointment_id}/cancel`
- **Router function**: `provider_cancel` (`coaching_router.py`)
- **Request schema**: `ReasonBody { reason: str }`
- **Response schema**: `ApiResponse` wrapping `appt.to_dict()`
- **Service method**: `CoachingAppointmentExecutionService.cancel_appointment(db, appointment_id, tenant_id, user_id, reason, actor_role="provider", request_id)`
- **Model / table**: `CoachingAppointment` / `coaching_appointments`
- **Principal role**: super_admin / tenant_owner / staff (technician,
  customer, guest denied by the guard)
- **Principal tenant**: `uuid.UUID(str(user.tenant_id))` — authoritative,
  never request-supplied
- **Principal user/staff ID**: `uuid.UUID(str(user.user_id))` passed as
  the `user_id` argument (note: unlike the 7 assignment-checked
  mutations, cancel does **not** pass a `staff_member_id` — the parameter
  does not exist on this method)
- **Appointment tenant**: `appt.tenant_id` (matched in `_get_appt`'s
  filter)
- **Assigned staff ID**: `appt.staff_member_id` (read but NOT compared —
  no assignment check, by design)
- **Current status → result status**: any legal source → `cancelled`
- **Cancellation reason**: required (`if not reason or not reason.strip():
  raise ERR_REASON_REQUIRED`); stored as both the event `notes` and
  `appt.failure_reason`
- **Current guard**: `require_owner_or_office_staff_mutation` (Slice 2F-12,
  access-scope-aware, technician excluded)
- **Tenant ownership check**: yes — `_get_appt(db, appointment_id,
  tenant_id)` filters `CoachingAppointment.tenant_id == tenant_id`
- **Assignment ownership check**: **NONE** — `_assert_staff_owns_appt`
  is deliberately not called (verified intentional, see
  `cancellation-policy-evidence.md`)
- **Transition validation**: yes — `_set_status` → `_assert_transition`
  runs before any mutation
- **Mutation order**: reason check → `_get_appt` (tenant) →
  `_assert_transition` → `appt.status = cancelled` → event row →
  `appt.failure_reason = reason` → `db.add` → `db.flush` → router
  `db.commit`
- **Audit event**: `CA_EV_CANCELLED` (`appointment_cancelled`), actor =
  `actor_user_id=user.user_id`, `actor_role="provider"` (coarse label,
  matches sibling `cancel_job`)
- **Notification event**: none — `coaching_service` has no notification
  infrastructure at all (confirmed by grep)
- **Frontend/API caller**: `coachingExecutionApi.cancel` (tenant-portal
  `lib/api.ts`) — but no `.tsx` component calls it (see
  `frontend-client-audit.md`)
- **Internal caller**: none — `cancel_appointment` is called only by
  `provider_cancel`
- **Alternate cancellation route**: `coaching_appointment.customer_router`'s
  `cancel_draft` — a DISTINCT model (`CoachingAppointmentDraft`, customer
  self-service), not the same record (see
  `alternate-cancellation-route-audit.md`)

## Policy is not inferred from the function name or the missing check
Per the mission's instruction, the business-wide conclusion is drawn from
the approved 2F-3B cross-module pattern (see
`cancellation-policy-evidence.md`), not from the absence of the
assignment check alone.
