# HS8B — API Mapping Report

| Ticket suggestion | Real route | Notes |
|---|---|---|
| `POST /v1/staff/jobs/{job_id}/complete` | `POST /v1/staff/service-jobs/{job_id}/complete` | Real prefix is `/service-jobs`, not `/jobs` — consistent with HS8's existing routes |
| `GET /v1/tenant/home-services/jobs/{job_id}/parts-requests` | `GET /v1/provider/service-jobs/{job_id}/parts-requests` | Real prefix is `/v1/provider/service-jobs`, not `/v1/tenant/home-services/jobs` — matches every other real tenant-facing job endpoint from HS8 |
| `POST .../parts-requests/{id}/approve` | `POST /v1/provider/service-jobs/{job_id}/parts-requests/{parts_request_id}/approve` | Matches, different prefix |
| `POST .../parts-requests/{id}/reject` | `POST /v1/provider/service-jobs/{job_id}/parts-requests/{parts_request_id}/reject` | Matches, different prefix |
| *(not in ticket's list, added for completeness)* | `POST /v1/staff/service-jobs/{job_id}/parts-requests` | Technician-side creation — required for the workflow to have an entry point at all |
| *(not in ticket's list)* | `GET /v1/staff/service-jobs/{job_id}/parts-requests` | Technician-side list |
| *(not in ticket's list)* | `POST /v1/provider/service-jobs/{job_id}/parts-requests/{id}/install` | Marks an approved part installed — required by the ticket's own test requirements (#10, #11) even though not in the API list |

## New this pass (all additive)
- 3 new staff endpoints: create/list parts requests, complete job.
- 4 new provider endpoints: list/approve/reject/install parts requests.
- New table `service_job_parts_requests` (migration 128).
- New column `service_jobs.completion_data` (migration 128).

## Verdict
API integration uses real data; route prefixes consistently follow the
established `/v1/staff/service-jobs` and `/v1/provider/service-jobs`
pattern from HS8 rather than the ticket's suggested `/v1/tenant/home-services/jobs`.
