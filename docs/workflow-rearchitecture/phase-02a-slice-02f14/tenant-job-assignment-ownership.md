# Tenant / Job / Assignment Ownership

## Ownership helpers (all pre-existing, correct, unmodified this slice)

- `_assert_assigned(job)` — `if actor_role in ("staff","technician") and job.assigned_staff_id != actor_id: raise NotFoundException(...)` → 404, hides existence from non-assigned technicians.
- `_assert_can_access_job(job)` — calls `_assert_assigned`, then additionally enforces `tenant_owner` (must be own tenant) and `customer` (must be own job). Full 3-way isolation for reads.
- `_get_job_for_assignment(job_id)` — used by `assign_staff`; enforces `tenant_owner`'s own-tenant match, 404 (`JOB_NOT_FOUND`) otherwise.
- `_get_job_for_staff_action(job_id)` — 404 if job missing; `if job.assigned_staff_id != actor_id: raise ServiceOSException("STAFF_NOT_ASSIGNED_TO_JOB", status_code=403)`. Role-agnostic — applies to any actor_role, used by all staff execution methods.

## Verification this slice

Re-verified (not modified) via `TestAssignmentOwnershipReVerified` in
`tests/test_phase2f14_field_ops_staff_authorization.py`: a technician assigned to job A cannot
read or mutate job B (403/404), a tenant_owner from tenant X cannot access a job belonging to
tenant Y (404), and a customer cannot access another customer's job (404).

## Conclusion

No IDOR was found across tenant, job, or checklist-item boundaries in the routes and service
methods audited this slice. See direct-authorization-idor-test-matrix.csv for the full route ×
persona × outcome matrix.
