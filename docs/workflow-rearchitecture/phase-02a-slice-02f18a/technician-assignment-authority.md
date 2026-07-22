# Technician Assignment Authority

## Assignment model
`ServiceJob.assigned_staff_id` (from `app.engines.final_records.models`) is
the sole assignment field consulted. `_resolve_job_for_thread` (new this
slice, `chat_service.py`) resolves a thread's linked record to its
`ServiceJob`:
- `record_type == "service_job"` → `db.get(ServiceJob, thread.record_id)`.
- `record_type == "service_booking"` → `select(ServiceJob).where(ServiceJob.booking_id == thread.record_id)`, first match.
- Any other `record_type` → `None` (not resolvable — falls back to
  active-participant policy, see `technician-capability-matrix.csv`).

No ID is ever adapted between pipelines: `field_ops.Job` is never queried by
this method, and `Booking` (legacy) is never queried — only
`app.engines.final_records.models.ServiceJob`/`ServiceBooking`, matching
Slice 2F-18's own established (and here re-confirmed, not re-derived)
finding that `quote_checklist`'s and this module's parent pipeline is
`ServiceJob`, not `field_ops.Job`.

## Verified (via `TestTechnicianThreadAccessPolicy`)
| Requirement | Test |
|---|---|
| Assignment belongs to principal tenant | Implicit — `thread.tenant_id` gates which tenant's `ServiceJob` a thread can even reference (create_thread's 2F-18 tenant-ownership check); the assignment check itself compares `job.assigned_staff_id` to the caller's own `user_id`, which cannot be spoofed (server-derived) |
| Technician identity matches authenticated principal | `actor_user_id` always JWT-derived, never body-supplied (unchanged from 2F-18) |
| Assignment references the exact Job attached to the conversation | `_resolve_job_for_thread` resolves FROM the thread's own `record_id`, not a client-supplied job id | `test_assigned_technician_allowed` |
| Unassigned technician denied | `test_unassigned_technician_denied` |
| Technician assigned to Job A cannot access Job B's conversation | `test_technician_assigned_to_other_job_denied` |
| Same-tenant technician substitution denied | `test_technician_tenant_membership_alone_is_not_sufficient` — proves shared `tenant_id` alone is insufficient |
| Removed/reassigned technician loses access | The assignment check is LIVE (queries `ServiceJob.assigned_staff_id` fresh on every access), not cached from a participant row created at thread-creation time — a technician removed from `assigned_staff_id` fails the very next access attempt automatically, no separate revocation step needed |

## Completed/cancelled Job behavior
Not separately gated by job status — a technician who WAS the last assigned
technician on a since-completed job retains access as long as
`assigned_staff_id` still points to them (jobs are not typically
reassigned away after completion in this codebase's existing workflow).
This mirrors the existing behavior for provider/staff (thread `status`
open/closed governs SENDING, not READING) and was not changed this slice —
flagged as a minor, non-blocking product question in
`product-decisions-required.md` rather than assumed.
