# FINAL-L5-01B — Jobs Source-of-Truth Inventory

Real inventory via `app.openapi()` (in-process, reliable regardless of live-server state) and direct model/router inspection — not assumption.

## Two parallel job systems confirmed to exist

### 1. `service_jobs` (canonical Home Services — per FINAL-L5-01 rule)
Model: `app/engines/final_records/models.py`. Populated by this sprint's and FINAL-L5-01's canonical seed (5 jobs, `L501-JOB-0001..0005`).

| Router | Prefix | Role | Table |
|---|---|---|---|
| `final_records/admin_router.py` | `/v1/admin/final-records` | Admin | `service_jobs` |
| `home_service_assignment/admin_router.py` | `/v1/admin/service-job-assignments`, `/v1/admin/service-jobs` | Admin (assignment ops) | `service_job_assignments` (FK to `service_jobs`) |
| `home_service_assignment/staff_router.py` | `/v1/staff/service-jobs` | Staff/Technician | `service_job_assignments` / `service_jobs` |
| `home_service_assignment/provider_router.py` | `/v1/provider/service-jobs` | Tenant/Provider | `service_job_assignments` / `service_jobs` |
| `final_records/provider_router.py` | `/v1/provider/my-records` | Tenant/Provider | `service_jobs` |
| `home_service_assignment/customer_router.py` | `/v1/customer/bookings` | Customer | `bookings` → `service_jobs` |
| `final_records/customer_router.py` | `/v1/customer/my-activity` | Customer | `service_jobs` |
| `final_records/confirm_router.py` | `/v1/customer/confirm` | Customer | booking→job confirmation flow |

### 2. `jobs` (legacy Field Ops — confirmed LEGACY per FINAL-L5-00's prior DB inventory finding)
Model: `app/engines/field_ops/models.py`, `__tablename__ = "jobs"`.

| Router | Prefix | Role |
|---|---|---|
| `field_ops/router.py` | `/v1/jobs` (general CRUD, quotes, checklists, invoicing, commission) | Mixed |
| `field_ops/staff_router.py` | `/v1/staff/me/jobs` | Staff |
| `field_ops/customer_router.py` | `/v1/customer/jobs` | Customer |
| `field_ops/admin_finance_router.py` | `/v1/admin/tenants/*` finance sub-routes | Admin (finance only) |

`/v1/jobs/admin/all` (tested in this sprint's earlier discovery of the `test_admin_jobs.py` pattern) is field_ops's own cross-tenant admin view — already correctly `require_super_admin`-gated, but it queries the **legacy** `jobs` table, not `service_jobs`.

## The mission's assumed route does not exist
`/admin/home-services/service-jobs` — confirmed via `app.openapi()` full path enumeration: **no such path exists anywhere in the mounted API.** This was already flagged in FINAL-L5-01; re-confirmed this sprint.

## Duplicate operation IDs (minor, unrelated finding)
FastAPI emits `UserWarning: Duplicate Operation ID` for several `admin_catalog`/`service_setup` routes during OpenAPI schema generation — a pre-existing code-hygiene issue, not a jobs-system issue, noted here only because it surfaced during this inventory's OpenAPI introspection.
