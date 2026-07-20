# CUSTOMER-L5-15 — Provider/Technician Assignment Impact

## What was verified

`HomeServiceJobAssignmentService.cancel_assignment`
(`app/engines/home_service_assignment/service.py` lines 361–406) is a
real, correct "unassign" method: nulls `ServiceJob.assigned_staff_id`,
sets `job.status = JOB_STATUS_PENDING_ASSIGNMENT`,
`job.assignment_status = JOB_ASSIGN_UNASSIGNED`, flips the
`ServiceJobAssignment` row's own status, and syncs the booking's
assignment status. It is correctly blocked
(`ERR_CANCEL_NOT_ALLOWED`) once a technician has already accepted.

**This method is never called by any cancellation or reschedule code
path** — confirmed by grepping every call site of `cancel_assignment`
across the repository: the only references are its own definition and
the provider-facing router endpoint that exposes it directly
(`POST /v1/provider/service-jobs/{job_id}/cancel-assignment`), which a
provider must trigger independently.

## Consequence

Cancelling a job via the only real cancel endpoint
(`POST /v1/provider/service-jobs/{job_id}/cancel`, provider-only) leaves
`ServiceJob.assigned_staff_id` and the assignment row completely
untouched. There is no automatic cascade from "job cancelled" to
"technician unassigned" anywhere in the backend.

## Why this client does not attempt to compensate

This client has no cancellation trigger at all (see
`baseline-verification.md`), so there is no client-side moment at which
"assignment invalidation" would need to be surfaced. If a future sprint
adds a real customer-facing cancel/reschedule endpoint, that backend
work should itself wire `cancel_assignment` into the cancellation
transaction (or an equivalent) — this is a backend orchestration gap,
not something a client can safely paper over (a client cannot force a
technician to become unassigned; it can only reflect what the backend
already did).

## Provider reacceptance / technician reassignment on reschedule

Not applicable for the same reason — no reschedule capability exists for
the canonical pipeline at all (see `reschedule-policy-contract.md`).
