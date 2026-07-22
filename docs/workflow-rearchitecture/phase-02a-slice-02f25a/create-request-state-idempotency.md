# create_request State and Idempotency — Slice 2F-25A

## Duplicate behaviour — explicit

```
ex = SELECT ReviewRequest WHERE job_id == job_id
if ex: return {"job_id": ..., "status": "already_exists", "idempotent": True}
```

A second request for the same job returns the idempotent marker rather than
raising or creating a second row. `uq_rvreq_job` enforces this at the database
level too.

## The ordering fix

The duplicate lookup is **global** (job_id is globally unique). Before this
slice it ran *first*, so a caller could supply another tenant's job number and
learn from `already_exists` that the job existed — a cross-tenant existence
oracle.

Ownership resolution now runs **before** it, so a foreign job number fails at
the Job lookup (`NotFound`) and never reaches the duplicate check. Asserted by
`test_ownership_precedes_the_duplicate_check`, which compares source positions.

## Job state

`ReviewRequestStatus.SENT` is set on creation, with
`expires_at = now + REVIEW_REQUEST_EXPIRY_DAYS` and `notified_at = now`.

**Final/completed/cancelled Job behaviour:** the engine does **not** check the
Job's status before creating a request. The internal caller only fires on job
close, so in practice requests are created for closed jobs — but the HTTP
route would accept any job in the tenant regardless of status. This is
**reported, not fixed**: gating on job status would be new product policy
about which job states may solicit a review. Recorded in
`product-decisions-required.md` and `known-limitations.md`.

## No partial state
Every rejection path raises before `db.add`. See
`no-partial-persistence-proof.md`.
