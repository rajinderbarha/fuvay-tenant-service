# FINAL-L5-01 — Booking and Job Lifecycle Integrity Report

| Job | Status | Assignment | Technician | Completion proof |
|---|---|---|---|---|
| L501-JOB-0001 | `new` | `unassigned` | none | n/a (correct — new job has no completion) |
| L501-JOB-0002 | `assigned` | `assigned` | Technician One | n/a (correct — not yet completed) |
| L501-JOB-0003 | `in_progress` | `assigned` | Technician One | n/a (correct — in progress, not completed) |
| L501-JOB-0004 | `completed` | `assigned` | Technician Two | Present — `completion_data` JSON with work summary, collected amount (775), notes, technician name, timestamp |
| L501-JOB-0005 | `cancelled` | `unassigned` | none | n/a (correct — cancelled, not completed) |

## Verified
- New booking has a valid initial status (`new`/`unassigned`) — confirmed.
- Assigned/in-progress jobs reference a real, active technician (`tech1@demo-ac-services.local`, `is_active=true`) — confirmed via the tenant isolation cross-join check (0 wrong-tenant assignments).
- Completed job (L501-JOB-0004) has a non-null `completion_data` — confirmed.
- Cancelled job has no completion record and no assignment — confirmed.
- No completed job lacks completion data — confirmed (only 1 completed job exists, and it has proof).
- No assignment references the inactive negative-test technician (`tech.inactive@demo-ac-services.local`) — confirmed, that user was deliberately never assigned to any job.
- Customer, tenant, and technician references are internally consistent — confirmed via the tenant isolation report's cross-join check.

**Result: PASS.** All 5 canonical job lifecycle states are represented with internally consistent references and correct completion-proof presence/absence.
