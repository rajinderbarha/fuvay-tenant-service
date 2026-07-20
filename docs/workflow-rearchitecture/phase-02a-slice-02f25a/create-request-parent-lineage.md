# create_request Parent Lineage — Slice 2F-25A

## The parent is `field_ops.Job`

| Link | Evidence |
|---|---|
| `ReviewRequest.job_id` is `String(100)`, unique | `models.py` — `uq_rvreq_job` |
| It holds `field_ops.Job.job_number` | `field_ops/service.py` job-close passes `job.job_number` |
| `field_ops.Job.job_number` is `String(30)`, unique | `field_ops/models.py` |
| `field_ops.Job.tenant_id` | non-null — the tenancy authority |
| `field_ops.Job.customer_id` | nullable — the customer authority |
| `field_ops.Job.assigned_staff_id` | nullable — the staff attribution |

## Pipelines explicitly NOT used

| Pipeline | Why not |
|---|---|
| `ServiceJob` | separate pipeline; this initiative has kept it separate since Slice 2F-14 and the mission forbids adapting identifiers |
| `Booking` / `ServiceBooking` | separate pipelines, kept separate throughout |

`job_id` is a **job_number string**, not a UUID, so it is not even
type-compatible with the UUID primary keys those pipelines use — a further
structural reason no adaptation is possible.

The verifier asserts `ServiceJob` and `ServiceBooking` appear nowhere in the
executable body of `create_review_request`, and the test suite asserts the
same against comment-stripped source.

## Chain of authority

```
principal (JWT)
   -> tenant_id                      [_effective_tenant]
        -> field_ops.Job             [job_number + tenant_id]
             -> customer_id          [derived]
             -> assigned_staff_id    [derived]
                  -> ReviewRequest
```

No link in that chain is client-supplied. The client supplies only the
`job_number` it wants a request for; everything else is resolved from the Job.

## Nullable customer
`Job.customer_id` is nullable. A job without a customer raises
`JOB_HAS_NO_CUSTOMER` rather than writing a request with a null or
client-supplied customer.
