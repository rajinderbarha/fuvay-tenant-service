# FINAL-L5-02B — Tenant Jobs Canonical Endpoint Inventory

The real endpoint family is `/v1/provider/my-records/*` (list/detail, read) + `/v1/provider/service-jobs/*` (assignment/scheduling actions), backed by `app/engines/final_records/provider_router.py` and `app/engines/final_records` (assignment). There is no literal `GET /v1/provider/service-jobs` list endpoint — the mission's illustrative names are not invented as new routes; the real, in-use paths are documented below (rule 8: no invented contracts).

| Method | Path | Router | Source table | Auth | Tenant-scope | Roles | Pagination | Filters | Frontend consumers | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| GET | `/v1/provider/my-records/jobs` | `final_records/provider_router.py` | `service_jobs` | `get_current_user` | `_get_tenant_id(user)` | tenant_owner, tenant_manager, tenant_readonly, technician (same-tenant) | `limit`/`offset`, `total` in response | `status` | `jobs/page.tsx`, `HomeServiceDashboard.tsx`, `staff/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| GET | `/v1/provider/my-records/jobs/{job_id}` | `final_records/provider_router.py` | `service_jobs` | `get_current_user` | tenant-scoped, cross-tenant → embedded not-found | same as above | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| GET | `/v1/provider/service-jobs/assignable` | assignment sub-router | `service_jobs` | `get_current_user` | tenant-scoped | tenant_owner/manager | — | `assignment_status` | (available, not currently consumed by a page) | **CANONICAL_ACTIVE** |
| GET | `/v1/provider/service-jobs/{job_id}/assignment-context` | assignment sub-router | `service_job_assignments` | `get_current_user` | tenant-scoped | tenant_owner/manager | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| GET | `/v1/provider/service-jobs/{job_id}/eligible-staff` | assignment sub-router | `staff` × `service_job_assignments` | `get_current_user` | tenant-scoped | tenant_owner/manager | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| POST | `/v1/provider/service-jobs/{job_id}/assign` | assignment sub-router | `service_job_assignments` | `get_current_user` | tenant-scoped, RO blocked | tenant_owner/manager | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| POST | `/v1/provider/service-jobs/{job_id}/cancel-assignment` | assignment sub-router | `service_job_assignments` | `get_current_user` | tenant-scoped, RO blocked | tenant_owner/manager | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| POST | `/v1/provider/service-jobs/{job_id}/schedule` | assignment sub-router | `service_job_assignments`/`service_jobs` | `get_current_user` | tenant-scoped, RO blocked | tenant_owner/manager | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| GET | `/v1/provider/service-jobs/{job_id}/timeline` | assignment sub-router | `service_job_assignment_events` | `get_current_user` | tenant-scoped | all same-tenant roles | — | — | `jobs/[id]/page.tsx` | **CANONICAL_ACTIVE** |
| GET | `/v1/jobs` and family (`/v1/jobs/{id}`, `/status`, `/close`, `/void`, `/notes`, `/media`, `/sla`, `/sla-alerts`, `/track/{token}`, `/tenants/{id}/counts`, quotes, `/spawn-repair`) | legacy `jobs` router | `jobs` (field_ops, 0 rows) | `get_current_user` | mixed | mixed | mixed | mixed | **0 Tenant Portal consumers** (all migrated); **super-admin still uses `/v1/jobs/admin/*`** for platform-wide oversight (different domain) | **LEGACY_COMPATIBILITY** (retained for super-admin's platform-wide domain — see Deprecation Report) |

Machine-readable version: `tenant-jobs-endpoint-inventory.json`.
