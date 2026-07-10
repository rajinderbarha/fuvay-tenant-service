# HS8 — API Mapping Report

| Ticket suggestion | Real route | Notes |
|---|---|---|
| `GET /v1/tenant/home-services/jobs` | `GET /v1/provider/service-jobs/assignable` | Different prefix (`/provider/` not `/tenant/home-services/`); fixed this pass (tenant-scoping bug) |
| `GET /v1/tenant/home-services/jobs/{job_id}` | `GET /v1/provider/service-jobs/{job_id}/assignment-context` | |
| `POST .../assign-technician` | `POST /v1/provider/service-jobs/{job_id}/assign` | Fixed this pass |
| `POST .../accept` | `POST /v1/staff/service-jobs/{job_id}/accept` | Technician-side, not tenant-side, in the real implementation |
| `POST .../status` | No single generic status endpoint — instead one dedicated endpoint per transition (`/on-the-way`, `/reached-site`, `/start-inspection`, `/complete-inspection`, `/start-service`, `/work-done`, `/customer-not-available`) | All under `/v1/staff/service-jobs/{job_id}/*`; all fixed this pass |
| `POST .../parts-request` | `POST /v1/staff/service-jobs/{job_id}/parts-required` | Real but minimal (note-only, no structured record) — see Parts Request report |
| `POST .../parts-request/{id}/approve` | *(does not exist)* | See Parts Request report |
| `POST .../complete` | `POST /v1/staff/service-jobs/{job_id}/work-done` | No payload/validation — see Completion Proof report |
| `GET /v1/staff/jobs` | `GET /v1/staff/service-jobs` | Fixed this pass |
| `GET /v1/staff/jobs/{job_id}` | `GET /v1/staff/service-jobs/{job_id}` | Fixed this pass |
| `GET /v1/customer/bookings/{booking_id}` | Matches (from HS7) | Confirmed reflects live job status |
| `GET /v1/admin/home-services/jobs` | Not found as a single list endpoint | Only job-scoped timeline endpoints found — see Admin Operations report |
| `GET /v1/admin/home-services/jobs/{job_id}` | `GET /v1/admin/service-jobs/{job_id}/assignment-timeline`, `.../execution-timeline` | Live-verified |

## Fixes made this pass (all additive/bugfix, no breaking route changes)
- `provider_router.py`: 8 handlers, `tenant_id` now correctly resolved from `user.tenant_id`.
- `home_service_assignment/staff_router.py`: 5 handlers, `staff_id` now resolved via real team-member lookup.
- `execution/home_service_router.py`: 13 handlers, `staff_member_id` now resolved the same way (was a hard crash before — no working code to break).
- `execution/home_service_service.py`: transition/ownership/reason errors now raise `ServiceOSException` (RFC 7807) instead of bare `ValueError`.
- 3 new migrations (125, 126, 127) fixing missing `updated_at` columns on `service_job_assignment_events`, `service_job_execution_events`, `service_job_media_uploads`.

## Verdict
API integration uses real data throughout; several real routes differ in
naming/prefix from the ticket's suggestions but are functionally
equivalent and now working end-to-end.
