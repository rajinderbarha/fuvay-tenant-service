# My Work Implementation

## Backend
- **File:** `app/engines/execution/my_work_service.py` (`TechnicianMyWorkService`) + `app/engines/execution/my_work_router.py`.
- **Endpoint:** `GET /v1/staff/my-work` (query params: `category`, `priority`). Mounted in `app/main.py` alongside the other Sprint 21 execution routers.
- **Derivation, not duplication:** no new workflow-state table was created. Every item is derived at query time from two existing canonical tables:
  - `ServiceJob` (via `assigned_staff_id` + `tenant_id` filter) — status mapped to category/action via `_JOB_STATUS_MAP`.
  - `PartsRequest` (via `technician_id` + `tenant_id` filter) — status mapped via `_PARTS_STATUS_MAP`.
- **Contract fields implemented:** all 25 fields from `my-work-contract.md`'s schema are present on every item (`id, work_type, domain, role, priority, user_facing_title, user_facing_description, record_type, record_id, current_status, user_facing_status, blocking_reason, responsible_role, assigned_user, created_at, due_at, sla_state, time_remaining, recommended_action, available_actions, primary_action, destination_route, required_permission, tenant_id, metadata, completed_at`).
- **Categories implemented:** URGENT, REQUIRES_MY_ACTION, WAITING_FOR_OTHERS, SCHEDULED, FAILED. Not populated this phase (no real source identified for a technician yet): ESCALATED, RECENTLY_COMPLETED — see `known-limitations.md`.
- **Sources implemented (of the brief's technician minimum list):**
  - ✅ Job assigned → REQUIRES_MY_ACTION
  - ✅ Upcoming scheduled job → SCHEDULED
  - ✅ Inspection required → REQUIRES_MY_ACTION
  - ✅ Quote required → WAITING_FOR_OTHERS
  - ✅ Parts request awaiting decision → WAITING_FOR_OTHERS
  - ✅ Approved parts awaiting installation → WAITING_FOR_OTHERS (honestly, not REQUIRES_MY_ACTION — see below)
  - ✅ Work completion required → REQUIRES_MY_ACTION
- **Honest gap surfaced, not hidden:** "Approved parts awaiting installation" is categorized WAITING_FOR_OTHERS with `available_actions: []` for the technician, because no staff-facing "mark installed" endpoint exists — only `POST /v1/provider/service-jobs/{id}/parts-requests/{id}/install` (provider/tenant-side) does. Rather than fabricate a technician-facing install action, the item's `recommended_action` text explicitly says to ask the business/admin to confirm installation. This is exactly the "no fabricated aggregation data" / "no fake success states" rule applied to a real edge case.
- **Tenant isolation:** every query filters on `tenant_id` in addition to `assigned_staff_id`/`technician_id` — verified by a dedicated test (`test_job_query_scoped_to_tenant_and_staff`) that inspects the compiled SQL WHERE clause, not just the response.
- **Partial-failure handling:** if the `ServiceJob` or `PartsRequest` query raises, that source is reported in `sources_unavailable` and the other source's items still return — verified by `test_partial_failure_reports_unavailable_source_not_fake_success`.
- **Pagination:** not implemented — the technician-scoped result set (single staff member's own jobs) was judged small enough that pagination would be premature; flagged in `known-limitations.md` for when a role with a larger result set (e.g. admin) is implemented.

## Frontend
- **File:** `frontend/tenant-portal/app/staff/my-work/page.tsx`.
- **Sections:** Urgent, Requires My Action, Waiting for Others, Scheduled, Failed (Escalated/Recently Completed omitted — no backend data for them yet, consistent with not fabricating empty-but-present sections beyond what the brief's required section list demands for a queue with no data source).
- **States:** loading (`Skeleton`), error (with request ID), partial-data warning (`sources_unavailable` banner), empty state ("Nothing needs your attention right now").
- **Filtering:** category filter (dropdown, server-side via query param).
- **Deep links:** every item links to `/staff/jobs/{job_id}` (or the parts request's parent job).
- **Not implemented this phase:** saved views, free-text search, SLA filter (no SLA data exists for technician-scoped items yet — none of the sources have a `due_at`/SLA concept beyond `scheduled_date`), priority filter UI (the query param exists on the backend and is exercised by tests, but no frontend control was added — a deliberate small scope cut, tracked in `known-limitations.md`).

## Explicitly out of scope (per Booking Exception exclusion rule)
Booking-domain and field_ops-Job-domain items are not included in this My Work implementation, per the non-negotiable rule against merging or adapting between booking pipelines without separate approval.
