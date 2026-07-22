# Appointment Assignment Model — Slice 2F-12A (Workstream 5)

## Assignment field
`CoachingAppointment.staff_member_id` (nullable UUID) — the staff member
assigned to deliver the appointment. Set at draft-confirmation time
(upstream of this router), not mutated by any route in
`execution.coaching_router`.

## The assignment helper
```python
def _assert_staff_owns_appt(self, appt, staff_member_id: uuid.UUID) -> None:
    if str(appt.staff_member_id) != str(staff_member_id):
        raise ValueError(ERR_STAFF_NOT_ASSIGNED)
```

## Which roles the helper affects (critical nuance)
The router computes the id it passes as
`staff_member_id = uuid.UUID(str(getattr(user, 'staff_member_id', None) or user.user_id))`.
`UserContext` has **no** `staff_member_id` attribute, so
`getattr(..., None)` is always `None` and the fallback `user.user_id`
always applies. Therefore for **every** persona (owner, staff,
super_admin), the helper compares `appt.staff_member_id` against
`user.user_id`.

**Consequence**: the 7 assignment-checked mutations are effectively
"the actor whose `user_id` equals the appointment's `staff_member_id`
only" — which blocks a **tenant_owner** too, unless the owner happens to
be the assigned staff member. This is the established, tested Slice 2F-12
behavior for accept/reject/start/complete/no-show/reschedule/notes.

## Why reusing `_assert_staff_owns_appt` for cancel would be WRONG
Because the helper compares against `user.user_id` uniformly, applying it
to cancel would **also block tenant_owner and super_admin** from
cancelling any appointment they are not personally the assigned staff of
— directly contradicting the approved 2F-3B cross-module policy that
whole-record cancellation is a **business-wide provider action** and
contradicting the mission's own required outcome that tenant-owner
cancellation authority be preserved. Applying it mechanically would break
the very personas the mission requires be preserved.

## Null / reassignment behavior
`staff_member_id` may be null (nullable column). For the 7
assignment-checked mutations, a null `appt.staff_member_id` would never
equal a real `user.user_id`, so those mutations would raise
`ERR_STAFF_NOT_ASSIGNED` — an unassigned appointment cannot be
accepted/started/etc. by anyone. Cancel, being business-wide, is
unaffected by a null assignment (correctly — an unassigned appointment
must still be cancellable by the business). No reassignment route exists
in this router.

## Decision
Because (a) the evidence proves business-wide cancellation is intentional
and approved (see `cancellation-policy-evidence.md`), and (b) mechanically
reusing `_assert_staff_owns_appt` would wrongly block owner/admin, **no
assignment check is added to cancel_appointment**. The correct, verified
policy is business-wide for the authorized provider persona — already the
current behavior. No role-aware check was needed, because the evidence
does not support restricting canonical staff to assigned-only for
cancellation (the approved sibling `cancel_job` admits staff business-wide
too).
