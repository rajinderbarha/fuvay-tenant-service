# HS8 — Job Assignment Report

## Bug found and fixed: tenant scoping used the wrong ID everywhere

Every handler in `app/engines/home_service_assignment/provider_router.py`
(8 endpoints: `/assignable`, `/{job_id}/assignment-context`,
`/{job_id}/eligible-staff`, `/{job_id}/assign`, `/{job_id}/reassign`,
`/{job_id}/cancel-assignment`, `/{job_id}/schedule`,
`/{job_id}/assignment-timeline`) computed `tenant_id = uuid.UUID(user.user_id)`
— using the logged-in tenant owner's own **auth user ID** as the tenant
scope, instead of `user.tenant_id` (a real, different UUID present on
`UserContext`). This meant `GET /v1/provider/service-jobs/assignable`
(and every other endpoint in this router) could **never return any real
job for any real tenant login** — confirmed live: `provider@serviceos.in`
saw `{"jobs": [], "count": 0}` despite 2 real, unassigned jobs existing
for that exact tenant.

Fixed: all 8 sites now use `uuid.UUID(user.tenant_id)`. Live-verified:
the same login now correctly returns both real jobs.

## Live-verified assignment flow
1. `GET /v1/provider/service-jobs/{job_id}/eligible-staff` → real active
   technician "Demo Staff" returned with `eligibility_status: eligible`,
   `match_reasons: [same_tenant, active, Technician]`.
2. `POST /v1/provider/service-jobs/{job_id}/assign` `{"staff_member_id": ...}`
   → `200`, `status: assigned`, real `assignment_id` created.
3. Repeated for a second real job — both assignments succeeded.

## Verdict
Job assignment: **fixed and live-verified working** for the real HS7
bookings. Not `NOT_READY_HS8_JOB_ASSIGNMENT_FAILED`.
