# create_request Authority — Slice 2F-25A

## Route
`POST /v1/reviews/requests` -> `create_request` -> `create_review_request`

## Why 2F-25's FULLY_PROTECTED was wrong

2F-25 pinned `tenant_id` to the principal and stopped there. But the handler
still read **`job_id` and `customer_id` from the request body**, and the
service verified neither. A tenant could therefore mint a review request:

- against a **job that does not exist** (`job_id` is a free string, not an FK)
- naming an **arbitrary customer**, including a customer of another tenant
- and probe **other tenants' job numbers**, because the duplicate check
  `select(ReviewRequest).where(job_id == job_id)` is global and returned
  `already_exists` for a foreign tenant's job

Tenant pinning alone does not prove parent ownership. The classification was
premature.

## After

```
tenant_id = self._effective_tenant(tenant_id)          # principal-derived
job = SELECT field_ops.Job
        WHERE job_number = job_id AND tenant_id = tenant_id
if job is None:               raise NotFound("Job")     # foreign == missing
if job.customer_id is None:   raise JOB_HAS_NO_CUSTOMER
if client customer != job.customer_id: raise CUSTOMER_MISMATCH
customer_id = job.customer_id                           # DERIVED
staff_id    = job.assigned_staff_id                     # DERIVED
... duplicate check runs only after ownership ...
```

## Requirements check

| Requirement | Status |
|---|---|
| Tenant is principal-derived | MET |
| Job exists and belongs to the exact tenant | **MET** (was absent) |
| Correct pipeline preserved | MET — `field_ops.Job`; no ServiceJob/Booking/ServiceBooking adaptation |
| Customer derives from the Job relationship | **MET** (was client-supplied) |
| Client cannot substitute another customer | MET — `CUSTOMER_MISMATCH` |
| Client cannot substitute another tenant | MET — `TENANT_ACCESS_DENIED` |
| Cross-tenant Job creation fails | MET — tenant predicate on the Job lookup |
| Customer/technician/guest cannot invoke | MET — `P.TENANT_UPDATE` |
| Read-only tenant actors denied | MET — `require_tenant_mutation_permission` |
| Unknown role/scope fail closed | MET |
| Duplicate behaviour explicit | MET — see `create-request-state-idempotency.md` |
| Denied requests write nothing | MET — `no-partial-persistence-proof.md` |

## The trusted internal path

`field_ops.service` on job close has already loaded the Job row and holds the
authoritative tenant and customer directly, so it calls with
`trusted_internal=True` and skips the re-lookup. The flag defaults to
`False`, so the HTTP route can never skip the proof — asserted by
`test_untrusted_caller_cannot_skip_the_parent_check`.

## Coverage
`create_request` retains its canonical row and its
`TENANT_MUTATION_PERMISSION_SCOPE_AWARE` status — but now on proven grounds
rather than assumed ones. The arithmetic is unchanged (212/229) because no
route was added or removed.
