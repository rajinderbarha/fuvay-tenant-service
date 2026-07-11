# FINAL-L5-01D — Tenant Jobs Endpoint Inventory

Real inspection of `app/engines/final_records/` and `app/engines/home_service_assignment/` plus live curl verification.

## Canonical Tenant Jobs endpoints (table: `service_jobs`)

| Method | Path | Router | Handler | Source table | Auth | Tenant scoping | Pagination |
|---|---|---|---|---|---|---|---|
| GET | `/v1/provider/my-records/jobs` | `final_records/provider_router.py` | `list_provider_jobs` | `service_jobs` | `get_current_user` | `_get_tenant_id(user)` derives tenant from JWT | `limit`/`offset`/`total` — real, verified live |
| GET | `/v1/provider/my-records/jobs/{job_id}` | `final_records/provider_router.py` | `get_provider_job` | `service_jobs` | `get_current_user` | Checks `job.tenant_id != tenant_id` → safe not-found | N/A |
| GET | `/v1/provider/service-jobs/assignable` | `home_service_assignment/admin_router.py` (provider_router) | `list_assignable` | `service_jobs` (assignment-filtered subset) | `get_current_user` | tenant-derived | count only, no offset |
| POST | `/v1/provider/service-jobs/{id}/assign` | same | `assign_job` | `service_job_assignments` | `get_current_user` | tenant-derived | — |
| POST | `/v1/provider/service-jobs/{id}/reassign` | same | `reassign_job` | `service_job_assignments` | `get_current_user` | tenant-derived | — |
| POST | `/v1/provider/service-jobs/{id}/cancel-assignment` | same | `cancel_assignment` | `service_job_assignments` | `get_current_user` | tenant-derived | — |
| POST | `/v1/provider/service-jobs/{id}/schedule` | same | `schedule_job` | `service_jobs` | `get_current_user` | tenant-derived | — |
| GET | `/v1/provider/service-jobs/{id}/assignment-timeline` | same | `get_timeline` | `service_job_assignment_events` | `get_current_user` | tenant-derived | — |
| GET | `/v1/provider/service-jobs/{id}/eligible-staff` | same | `get_eligible_staff` | `service_job_assignments` join `users` | `get_current_user` | tenant-derived | — |

**Decision: `GET /v1/provider/my-records/jobs` (+ `/{job_id}`) is the canonical Tenant Jobs list/detail endpoint** — proper pagination envelope (`items`/`total`/`limit`/`offset`), correct tenant-scoping, backed by `service_jobs`. The `/v1/provider/service-jobs/*` family is the canonical **assignment/lifecycle action** family (assign/reassign/schedule/cancel/timeline), used alongside the list/detail pair.

## Legacy `/v1/jobs` endpoints (table: `jobs`, field_ops engine)

| Method | Path | Router | Source table | Status |
|---|---|---|---|---|
| GET | `/v1/jobs` | `field_ops/router.py` | `jobs` | LEGACY — requires explicit `tenant_id`, returns `422 TENANT_REQUIRED` when frontend's `getTenantId()` call shape doesn't satisfy it |
| GET | `/v1/jobs/{id}` | same | `jobs` | LEGACY |
| PUT | `/v1/jobs/{id}/status` | same | `jobs` | LEGACY |
| PUT | `/v1/jobs/{id}/checklist` | same | `jobs` | LEGACY — checklist concept doesn't exist on `service_jobs` |
| GET | `/v1/jobs/sla-alerts` | same | `jobs` | LEGACY |
| POST | `/v1/jobs/{id}/close` | same | `jobs` | LEGACY — `job_type`-aware close (repair/service/consultation), no `service_jobs` equivalent |
| POST | `/v1/jobs/{id}/quotes` | same | `job_quotes` | LEGACY — quote workflow, no `service_jobs` equivalent |

## Machine-readable
`tenant-jobs-endpoint-inventory.json`.
