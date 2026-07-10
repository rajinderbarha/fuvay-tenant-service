# HS8 — Technician Workflow Report

## Bugs found and fixed

1. **`home_service_assignment/staff_router.py` — same ID-confusion bug as
   the provider router.** All 5 handlers (`GET ""`, `GET /{job_id}`,
   `POST /{job_id}/accept`, `POST /{job_id}/reject`,
   `GET /{job_id}/assignment-timeline`) used `staff_id = uuid.UUID(user.user_id)`
   — the technician's raw auth user ID — to match against
   `ServiceJob.assigned_staff_id`, which actually stores
   `provider_team_members.id` (a different UUID). A real technician login
   (`staff@serviceos.in`) could never see any job assigned to them, even
   immediately after a correct assignment. Fixed with a
   `_resolve_staff_member_id()` helper that looks up the real team-member
   row via its `user_id` FK.

2. **`execution/home_service_router.py`'s staff router — `UserContext`
   has no `staff_member_id` field at all.** Every one of its 13 handlers
   (`on-the-way`, `reached-site`, `start-inspection`, `complete-inspection`,
   `start-service`, `work-done`, `customer-not-available`,
   `quote-required`, `parts-required`, `notes`, `diagnosis-notes`,
   `media`, plus `accept`/`reject` which are shadowed by the router
   above) called `uuid.UUID(str(user.staff_member_id))`, evaluating to
   `uuid.UUID("None")` and crashing every single call with a 500 —
   confirmed live via `POST .../on-the-way`. Fixed with the same
   team-member-lookup pattern.

3. **Invalid status transitions raised bare `ValueError`, uncaught by any
   router handler**, surfacing as raw 500s instead of the ticket's
   required clean 422. Fixed by converting `_assert_transition`,
   `_get_job`, `_assert_staff_owns_job`, and both reason-required checks
   in `home_service_service.py` to raise `ServiceOSException` (caught by
   the app's existing global RFC 7807 handler — no per-router try/except
   needed).

## Live-verified full technician workflow (real job, real DB)
`accept` → `on-the-way` → `reached-site` → `start-inspection` →
`complete-inspection` → `start-service` → `work-done`, each step
returning the updated real `ServiceJob` row with the correct `status`.
A work note was added and a completion photo (`after_photo`) was
uploaded successfully (after fixing a 4th missing-`updated_at`-column
table, `service_job_media_uploads`, migration 127).

## Verdict
Technician workflow: **fixed and live-verified working end-to-end**
for the full lifecycle. Not `NOT_READY_HS8_TECHNICIAN_WORKFLOW_FAILED`.
