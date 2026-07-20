# Job Review-Request Read Authority — Slice 2F-25A

## Route
`GET /v1/reviews/requests/jobs/{job_id}` -> `get_review_request`

## The exact Job model — no pipeline adaptation

`ReviewRequest.job_id` is a `String(100)` holding **`field_ops.Job.job_number`**.
Established by the only internal writer: `field_ops.service` passes
`job.job_number` on job close.

It is **not** `ServiceJob`, **not** `Booking`, **not** `ServiceBooking`. No
identifier is adapted between pipelines, and the verifier asserts the absence
of those names in executable code.

## Before
`select(ReviewRequest).where(ReviewRequest.job_id == job_id)` — no scoping at
all. Any authenticated principal could read any tenant's review-request status
and its `review_id` by guessing a job number.

## After — persona-scoped

| Principal | Scope |
|---|---|
| `customer` | `ReviewRequest.customer_id == actor_id` — only requests addressed to them |
| any other tenant-side principal | `ReviewRequest.tenant_id == actor_tenant_id` |
| `super_admin` | explicitly unscoped |
| no tenant context (non-customer) | fails closed before any query |

## Requirements check

| Requirement | Status |
|---|---|
| Job belongs to the principal tenant or authenticated customer | MET — enforced on the `ReviewRequest` row, which carries both keys |
| Customer owns the exact Job relationship | MET — `customer_id` predicate |
| Cross-tenant Job IDs fail | MET |
| Technician access requires active assignment | **N/A** — technicians are not separately admitted; they fall under the tenant predicate. Narrowing to assignment would be new policy. |
| Same-tenant unrelated Job IDs | **permitted** — any principal of the owning tenant may read its own tenant's request status. This is the established tenant-visibility model in this engine; narrowing it further would be invented policy. Recorded as a product question. |
| Status fields expose nothing customer-private or moderation-related | MET — see `residual-field-privacy.csv`; `customer_id` and `staff_id` are predicates, never serialized |
| Missing and unauthorized are equivalent | MET — both `ReviewRequest` not-found |

## Frontend
No caller found in any of the six applications.
