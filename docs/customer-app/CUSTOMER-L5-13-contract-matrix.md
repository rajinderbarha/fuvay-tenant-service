# CUSTOMER-L5-13 — Contract Matrix

Verified by direct reading of `app/engines/execution/home_service_service.py`,
`home_service_router.py`, `models.py`, `constants.py`,
`app/engines/home_service_assignment/staff_model.py`,
`app/engines/geo/models.py`, `service.py`, `router.py`,
`app/engines/customer_reviews/models.py`, `public_router.py`,
`app/engine_registry/registry.py`, `app/main.py` — cross-checked by an
independent background research pass.

## Endpoint Used

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/customer/service-jobs/{jobId}/tracking` | Real, customer-facing service-execution timeline — `{job, notes, media, timeline}`, built from `ServiceJobExecutionEvent` (real, live-written by staff-facing endpoints). |
| `GET` | `/v1/customer/my-activity/bookings/{bookingId}` | Reused, unchanged from CUSTOMER-L5-11 — the only real source for this client to resolve a booking's `job.id` (needed as the path param for the tracking endpoint above, since no other real customer endpoint returns a raw job ID). |

## Endpoints/Capabilities Investigated and Confirmed Absent or Unreachable

| Concept | Real backend state | Parity status |
|---|---|---|
| Customer-facing technician profile (name/photo/verification/badges/experience/skills/languages) | `ProviderTeamMember` model has `full_name`/`profile_photo_url`/`skills` columns, but **zero customer-facing endpoints join to this table** | `MISSING_BACKEND` |
| Aggregate technician rating for customers | `StaffRatingSummary` real, computed, but only exposed via admin/provider routers | `MISSING_BACKEND` (computed, not exposed) |
| Live GPS technician location | `geo.StaffLocation` real, upsert-updated table exists — but only written/read by the separate, legacy, disabled-by-default `field_ops`/`dispatch`/`booking` engines, never by the real `home_service_booking`/`home_service_assignment`/`execution` pipeline | `MISSING_BACKEND` (orphaned from this pipeline) |
| Real-time transport (websocket/SSE) | Zero `@app.websocket`/SSE routes exist anywhere in `app/main.py` (only an aspirational doc-comment) | `MISSING_BACKEND` |
| ETA for a specific assigned technician | `geo/service.py` computes a crude `eta_minutes = road_dist/0.5` heuristic — only for a disconnected dispatch-radius search, never for a specific assigned technician's job | `MISSING_BACKEND` |
| Route/directions summary | No `mapbox`/`google maps`/directions integration exists anywhere in `app/` | `MISSING_BACKEND` |
| Masked-call / in-app contact | Zero hits repo-wide for `masked_call`/`proxy_number`/`click_to_call`/`contact_technician` | `MISSING_BACKEND` |
| Tracking-session model (authorization/expiry) | No such model exists — the real tracking data is a stateless, always-re-fetchable timeline | `NOT_APPLICABLE` (no session concept to model) |
| Booking-level cancel/reschedule execution (already known from L5-12) | Still absent, unchanged | `MISSING_BACKEND` |

## `GET /v1/customer/service-jobs/{jobId}/tracking` — Full Contract

- **Request**: `jobId` (a real `ServiceJob.id`, obtained via the reused
  L5-11 booking-detail endpoint's `job.id` field — this endpoint itself
  has no way to resolve a job from a booking ID directly).
- **Response**: `{"job": <ServiceJob.to_dict()>, "notes": [...], "media": [...], "timeline": [...]}`.
  - `job`: full `ServiceJob.to_dict()` — this client parses **only**
    `status` from it (structurally, via selective schema field inclusion
    — every other field, including `assigned_staff_id`, is never parsed,
    matching the established "exclude via `z.object()` omission"
    security pattern from prior sprints).
  - `notes`: `ServiceJobExecutionNote.to_dict()` rows — but **the
    customer router does not pass `customer_only=True`** for the
    `/tracking` endpoint specifically (only the notes/media are filtered
    that way — confirmed by direct reading), meaning this response could
    theoretically include internal, non-customer-visible notes. **This
    sprint's client does not render the `notes` array at all** — a
    deliberate, disclosed mitigation for a real, disclosed backend gap
    (see `privacy-and-security-review.md`).
  - `media`: same real, potential over-exposure — **not rendered this
    sprint** either, for the same reason (this sprint's real scope is the
    status timeline only, not a media gallery — a real, separate feature
    a future sprint could build once the backend's own filtering is
    verified/fixed).
  - `timeline`: array of `ServiceJobExecutionEvent.to_dict()` rows:
    `{id, job_id, event_type, old_status, new_status, notes, actor_role,
    created_at}`. This client's schema deliberately omits `id`, `job_id`,
    `notes`, and `actor_role` (the `notes` field here is the same
    real, disclosed leak-risk as the top-level `notes` array — an event's
    own `notes` field is not customer-visibility-flagged at all) —
    parsing only `event_type` and `created_at`.

## Real Event Types (`app/engines/execution/constants.py`) — Classification

| Real `event_type` | Real trigger (staff endpoint) | This sprint's customer-safe label |
|---|---|---|
| `job_accepted` | `POST /v1/staff/service-jobs/{id}/accept` | "Technician accepted the job." |
| `job_rejected` | `POST /v1/staff/service-jobs/{id}/reject` | "Provider is finding another technician." |
| `job_scheduled` | `POST /v1/staff/service-jobs/{id}/schedule` | "Visit scheduled." |
| `technician_on_the_way` | `POST /v1/staff/service-jobs/{id}/on-the-way` | "Technician is on the way." |
| `technician_reached_site` | `POST /v1/staff/service-jobs/{id}/reached-site` | "Technician has arrived." |
| `inspection_started` | `POST /v1/staff/service-jobs/{id}/start-inspection` | "Inspection started." |
| `inspection_completed` | `POST /v1/staff/service-jobs/{id}/complete-inspection` | "Inspection completed." |
| `service_started` | `POST /v1/staff/service-jobs/{id}/start-service` | "Service in progress." |
| `work_done` | `POST /v1/staff/service-jobs/{id}/work-done` | "Work completed." |
| `customer_not_available` | Real, staff-triggered | "Technician could not reach you at the scheduled time." |
| `job_cancelled` | Real, staff-triggered | "Booking cancelled." |
| `job_failed` | Real, staff-triggered | "Booking could not be completed." |
| `quote_required`/`parts_required` | Real, staff-triggered | "Provider needs your approval to continue." (parts-approval execution itself remains out of this sprint's explicit scope) |
| `diagnosis_added`/`before_photo_uploaded`/`after_photo_uploaded`/`work_note_added` | Real, staff-triggered | Not rendered this sprint — these are execution detail (notes/media), not status-milestone events; showing them would require the notes/media rendering this sprint deliberately defers (see above) |

## `job.status` Real Values — Classification

`pending_assignment`, `assigned`, `accepted`, `scheduled`, `on_the_way`,
`reached_site`, `inspection_started`, `inspection_done`, `quote_required`,
`service_started`, `work_done`, `completed`, `cancelled`, `failed`,
`customer_not_available` — all real, confirmed reachable via the
`execution` engine's own real state machine (`JOB_TRANSITIONS`). Added to
the shared, centralized status registry (`features/bookings/domain/booking-status-registry.ts`,
originally built by CUSTOMER-L5-12) rather than duplicated into a second
registry — see `tracking-architecture.md`.

## Error Contract

No new error codes beyond what's already handled by this endpoint's
generic `ok()`/exception-handler pattern (unchanged infrastructure since
earlier sprints). A missing/foreign job returns a raised
`ValueError(ERR_RECORD_NOT_FOUND)` — per the same disclosed,
cross-cutting "unhandled `ValueError` falls through to a generic 500"
gap documented in `CUSTOMER-L5-11-contract-matrix.md` (unchanged,
not fixed this sprint, out of scope).
