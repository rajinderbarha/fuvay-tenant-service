# Tenant/Customer Authority Boundary — Slice 2F-12 (Workstream 5)

## Tenant-side (staff/provider) mutations
- **Principal tenant is authoritative**: `tenant_id` is always
  `uuid.UUID(str(user.tenant_id))` from the authenticated principal —
  never request-supplied (no route schema in this module has a
  `tenant_id` field).
- **Appointment belongs to the principal tenant**: `_get_appt(db,
  appointment_id, tenant_id)` filters `CoachingAppointment.tenant_id ==
  tenant_id` — a foreign-tenant appointment ID simply doesn't match,
  raising `ERR_RECORD_NOT_FOUND` (no distinguishable "exists but denied"
  response).
- **Assignment ownership** (7 of 8 mutations): `_assert_staff_owns_appt`
  requires exact match between the appointment's `staff_member_id` and
  the calling staff member's own `user_id` (the established
  `staff_member_id == user.user_id` convention, `app/core/staff_scope.py`).
  A staff member from the same tenant, but not assigned to this specific
  appointment, is denied (`ERR_STAFF_NOT_ASSIGNED`).
- **`cancel_appointment` is the one exception** — it does not call
  `_assert_staff_owns_appt` at all (confirmed by source read). Any
  tenant_owner/staff of the correct tenant may cancel, not only the
  assigned staff member. Documented as intentional (business-wide
  cancellation authority), not a defect — see
  `coaching-capability-ownership.csv`.
- **[Fixed this slice] Persona ownership**: `require_owner_or_office_staff_mutation`
  now gates every mutation; `require_owner_or_office_staff_read` gates
  the 2 staff/provider reads — previously any authenticated role could
  reach these routes.

## Customer-side (tracking) authority
- **Canonical customer role required**: `require_customer` (fixed this
  slice).
- **Authenticated principal is authoritative**: `customer_id` is always
  `uuid.UUID(str(user.user_id))`, never request-supplied.
- **Appointment/customer relationship checked**: inline query filters
  `CoachingAppointment.id == appointment_id AND CoachingAppointment.customer_id
  == uuid.UUID(str(user.user_id))` together.
- **Tenant/provider is derived from the appointment**: `appt.tenant_id`
  is read from the fetched record, passed to `get_notes`.
- **Customer routes do not require tenant mutation access scope**:
  `require_customer` has no access-scope concept.

## Foreign ID rejection (all verified this slice)
Foreign lead/appointment/note IDs across tenant and customer boundaries
are all rejected via the mechanisms above — see
`direct-authorization-idor-test-matrix.csv`.
