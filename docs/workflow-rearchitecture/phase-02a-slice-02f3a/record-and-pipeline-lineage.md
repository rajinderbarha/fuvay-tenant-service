# Record and Pipeline Lineage — Workstream 3

## Central finding
All 29 mutation routes across the 3 audited modules operate on **exactly one
pipeline**: `app.engines.final_records.models.ServiceJob` (plus its
job_id-linked satellite tables `ServiceJobAssignment`, `PartsRequest`,
`ServiceJobExecutionNote`, `ServiceJobMediaUpload`). There is **no
Booking/Job/ServiceBooking pipeline confusion** within these 3 modules —
that overlap (if any) lives elsewhere (field_ops's legacy `Job` model,
already found dead/disconnected in prior slices per project memory:
L5-35/36 found `field_ops` jobs table has 0 real rows vs `service_jobs`'
real data).

## Record types confirmed by direct source reading
- **`ServiceJob`** (`app.engines.final_records.models`) — the canonical
  execution record. Every route in `execution.home_service_router` (except
  the 3 PartsRequest-specific ones) loads this model, scoped by `job_id`
  (+ `tenant_id` in most execution-router handlers via `_get_job`).
  `home_service_assignment`'s `_load_job()` also loads this exact model —
  **same table, same primary key space** — confirming these two modules
  operate on the identical record type, not parallel pipelines.
- **`ServiceJobAssignment`** — a separate table tracking the
  current/historical technician assignment for a `ServiceJob`
  (`job_id` FK, `assigned_staff_member_id`, `assignment_status`,
  `is_current`). Owned exclusively by `home_service_assignment` (both
  `staff_router` and `provider_router`); `execution.home_service_router`
  never touches this table directly (it reads/writes `ServiceJob.status`
  and `ServiceJob.assignment_status` columns, not the `ServiceJobAssignment`
  row itself).
- **`PartsRequest`** (`app.engines.execution.models`,
  table `service_job_parts_requests`) — `job_id` + `tenant_id` +
  `technician_id` columns, confirmed FK'd to `ServiceJob`. Owned
  exclusively by `execution.home_service_router` — zero references
  anywhere in `home_service_assignment`.

## Can the same real-world booking produce records in both pipelines?
**Yes, by design, not by accident.** A single `ServiceJob` row is the
shared record both modules operate on — `home_service_assignment` manages
its assignment lifecycle (who is assigned, whether they've accepted), while
`execution.home_service_router` manages its execution lifecycle (on-the-way,
inspection, work, completion) and its `PartsRequest`/note/media satellites.
This is not a pipeline-crossing risk — it's the intended division of labor
between two modules cooperating on one record, confirmed by direct source
reading rather than assumed.

## The one genuine duplication: accept/reject
The single exception is `accept`/`reject` — both modules implement this
capability on the same `ServiceJob` (execution's version additionally reads
`ServiceJobAssignment` only implicitly via `_assert_staff_owns_job`, while
home_service_assignment's version explicitly loads and validates against
`ServiceJobAssignment`). Both are mounted at the identical path; only one
executes (see `canonical-route-disposition.csv`). This is the one place
where the "cooperating division of labor" model breaks down into an actual
duplicate — likely a historical artifact of Sprint 21 (execution) rebuilding
a capability Sprint 20 (assignment) had already shipped, without removing
or referencing the earlier version.

## UNVERIFIED items (explicitly, not guessed)
- Whether `execution.home_service_router`'s `staff_accept_job`/
  `staff_reject_job` were ever intentionally meant to replace
  `home_service_assignment`'s versions (i.e., an incomplete migration) or
  were an independent, accidental re-implementation. No commit message,
  changelog, or code comment was found clarifying original intent —
  **UNVERIFIED**, not assumed either way.
- Whether other verticals (`execution.coaching_router`,
  `execution.real_estate_router`) have similar shadowing against their own
  assignment modules — **out of scope for this slice** (only the 3 named
  home-service modules were audited).
