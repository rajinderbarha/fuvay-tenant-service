# CUSTOMER-L5-13 — Baseline Verification

## Previous Sprint Verification

| Sprint | Claimed status | Verified status | Notes |
|---|---|---|---|
| CUSTOMER-L5-00 through L5-12 | PARTIAL (documented) | Confirmed PARTIAL, unchanged | No regressions; 608 tests passing at sprint start. |

1. Authentication: confirmed working, unmodified since L5-02.
2. Current customer loads: confirmed.
3. Canonical booking exists: confirmed (L5-11).
4. Canonical service job exists where required: confirmed — one booking → zero-or-one job, created atomically (L5-11/L5-12).
5. Booking-to-job relation correct: confirmed, unchanged.
6. Assignment state is real: confirmed (L5-12) — `assignment_status`/`assignment_message`, real `ServiceJobAssignment`/`ServiceJobAssignmentEvent`.
7. Assigned technician record canonical: confirmed real (`ServiceJob.assigned_staff_id` → `ProviderTeamMember`), but **re-verified this sprint that no customer-facing endpoint ever joins to it** — see Central Findings.
8. Technician belongs to correct Tenant: confirmed enforced server-side (`ProviderTeamMember.tenant_id`, assignment queries scoped by tenant).
9. Technician assigned to correct job: confirmed (`ServiceJobAssignment.job_id`).
10. Provider acceptance complete where required: re-scoped, unchanged from L5-12 (technician-level `assignment_status`, not a separate tenant-level decision).
11. Tracking action backend-authorized: **re-scoped this sprint** — no live-GPS tracking authorization concept exists; the real, reachable "tracking" this sprint builds is a status/event timeline, always available once a job exists (no separate authorization gate needed or found).
12. Dispatch and on-the-way statuses identified: **major correction to CUSTOMER-L5-12's own finding** — see Central Findings.
13. Live-location source identified: confirmed **absent** for the real customer pipeline (see Central Findings — a real live-GPS table exists but is architecturally orphaned from this pipeline).
14. Tracking-session endpoint identified: **no session concept exists** — the real tracking data is a stateless, re-fetchable timeline, not a session with authorization/expiry.
15. Real-time update infrastructure identified: confirmed **absent** — no websocket/SSE endpoint exists anywhere in the FastAPI app (only an aspirational doc comment in `main.py`, no actual route).
16. Map provider and key handling identified: `react-native-maps` is already an installed mobile dependency, confirmed **unused by any screen** — and, per finding 13, there is no coordinate data to render even if a map screen were built.
17. Customer-safe contact policy identified: confirmed **absent** — no masked-call/proxy-number/click-to-call system exists anywhere in the backend.
18. Technician-profile visibility policy identified: confirmed **no customer-facing technician profile exists at all** — see Central Findings.
19. Assignment-change behavior identified: confirmed real and unchanged from L5-12 (`assignment_reassigned` event, `_ASSIGNMENT_DISPLAY` customer-safe mapping).
20. No fake technician or location in production paths: confirmed — no technician/tracking/map code exists anywhere in the mobile app before this sprint.
21. Existing tests pass: confirmed — 608/608 at sprint start.
22. Working tree: understood — unrelated parallel work in other engines/frontends, none touched.
23. No unrelated changes overwritten: confirmed.

## Central Findings

### 1. Correction to CUSTOMER-L5-12's "status sequence stops at scheduled" finding

L5-12's research (and this sprint's own initial pass) found that
`final_records/constants.py`'s own `JOB_STATUS_DISPATCHED`/
`JOB_STATUS_IN_PROGRESS`/`JOB_STATUS_COMPLETED`/`JOB_STATUS_CANCELLED`
constants are never assigned by any real code path — which is still true
for **those specific constant names**. However, this sprint discovered a
**separate, real, live execution engine** (`app/engines/execution/`,
Sprint 21) with its **own**, differently-named but still-real status
constants (`app/engines/execution/constants.py`) that genuinely are
written to the *same* `ServiceJob.status` column via real, permission-checked
staff endpoints (`POST /v1/staff/service-jobs/{jobId}/on-the-way`,
`/reached-site`, `/start-inspection`, `/complete-inspection`,
`/start-service`, and others):

```
pending_assignment → assigned → accepted → scheduled
  → on_the_way → reached_site → inspection_started → inspection_done
  → (quote_required) → service_started → work_done → completed
  (or → customer_not_available / cancelled / failed at various points)
```

This is a real, working, enforced state machine
(`execution/constants.py`'s `JOB_TRANSITIONS`), confirmed by an
independent research pass. **This corrects, for this sprint's purposes,
CUSTOMER-L5-12's documented "unreachable past `scheduled`" finding** — it
was accurate for the specific constants L5-12 searched for, but this
sprint's own, deeper search into the previously-deferred `execution`
engine found the real mechanism. This is not a defect in L5-12's work
(its own docs explicitly deferred investigating `execution/` to this
sprint) — it is exactly the intended handoff.

### 2. Real, Richer Timeline Exists — `GET /v1/customer/service-jobs/{jobId}/tracking`

This endpoint (`execution/home_service_router.py`) returns
`{job, notes, media, timeline}` where `timeline` is built from
`ServiceJobExecutionEvent` rows — including real `technician_on_the_way`/
`technician_reached_site`/`inspection_started`/`inspection_completed`/
`service_started`/`work_done` events. This is genuinely richer than
CUSTOMER-L5-12's `ServiceJobAssignmentEvent`-based timeline (which only
covers `pending_assignment → assigned → accepted → scheduled`). This
sprint builds its real "Service Tracking" screen against this endpoint,
reusing the already-reserved `tracking` route (`route-registry.ts`,
`productionEnabled: false` until this sprint).

### 3. Decisive: No Real Customer-Facing Technician Profile Exists

`ProviderTeamMember` (the real staff/technician model) has `full_name`,
`profile_photo_url`, `skills` (JSONB) columns — but **no customer-facing
endpoint anywhere joins to this table**. The only technician-related data
any customer-facing router ever returns is a bare `assigned_staff_id`
UUID (never resolved to a name) or a generic `actor_role`/customer-safe
event label (e.g., "Technician assigned.") — never an individual
technician's identity. This sprint therefore builds **no** technician
profile screen (§11/§12 of the spec) — there is no real data to render,
and fabricating a name/photo would be a direct violation of this
project's central discipline. Documented exhaustively in
`technician-profile-contract.md`.

### 4. Decisive: No Live GPS, Map, ETA, Route, or Contact Capability Exists for This Pipeline

A real live-GPS table (`app/engines/geo/models.py`'s `StaffLocation`) and
a crude ETA heuristic (`geo/service.py`'s `eta_minutes = road_dist/0.5`)
genuinely exist in this codebase — but are **architecturally orphaned**
from the real customer booking pipeline: they are only ever
read/written by a separate, legacy, `is_enabled_by_default: False`
dispatch stack (`field_ops`/`dispatch`/`booking` engines), never by
`home_service_booking`/`home_service_assignment`/`execution` (the engines
that actually power this app). No websocket/SSE endpoint exists anywhere.
No masked-call/contact system exists anywhere. `react-native-maps` is
already an installed mobile dependency but has no coordinate source to
render for this pipeline. This sprint builds a real, honest,
**non-map, status-milestone-based** tracking experience instead — exactly
the "non-map tracking fallback" the spec itself explicitly allows for,
and explicitly does not build a map, marker, live location, ETA
countdown, route, or masked-call action anywhere.

### 5. A Real, Computed Technician Rating Aggregate Exists — But Is Not Customer-Reachable

`StaffRatingSummary` (`app/engines/customer_reviews/models.py`) is a
real, computed, per-technician rating aggregate — but is only exposed via
admin/provider-facing endpoints. No customer-facing endpoint reads it.
This sprint does not fabricate a customer-facing technician rating
display as a result.

## Blockers

None preventing implementation of an honestly-scoped sprint.

## Corrections Completed

None to prior sprints' code. `BookingDetailScreen.tsx`'s (L5-12)
`actionTrack` informational row is promoted this sprint to a real,
interactive action (navigating to the newly-real `Tracking` screen) — an
expected, planned boundary promotion, not a correction of a defect.

## Deferred Issues

See `CUSTOMER-L5-13-known-gaps.md`.
