# No Partial Persistence Proof — Slice 2F-25A

## create_request rejection ordering

1. `_effective_tenant` -> `TENANT_ACCESS_DENIED` (tenant mismatch / no context)
2. Job lookup -> `NotFound("Job")` (missing or foreign)
3. `job.customer_id is None` -> `JOB_HAS_NO_CUSTOMER`
4. client/job customer mismatch -> `CUSTOMER_MISMATCH`
5. duplicate check -> idempotent early return
6. **`db.add(req)`** <- first write
7. `db.flush()`

Steps 1-4 are all reads and raises. The first write is step 6.

## Empirical proof

`test_every_rejected_create_writes_nothing` drives all three rejection classes
against a session double and asserts:

```
db.add.assert_not_called()
db.flush.assert_not_called()
db.commit.assert_not_called()
```

The tenantless cases additionally assert `db.execute.assert_not_called()` --
the guard fires before a query is issued.

## For every denied create_request

| Artifact | State |
|---|---|
| `ReviewRequest` row | none created |
| Review row | unchanged |
| Review status | unchanged |
| Aggregate | unchanged (not reached) |
| Audit / domain event | none — `_publish` is not on this path |
| Notification | none |
| Commit | never reached |
| Existing records | unchanged |

## GET routes perform no mutation

`test_read_methods_perform_no_writes` asserts that `get_aggregate`,
`get_review_request`, `list_by_customer` and `get_review` contain no
`db.add(` and no `commit()`. Verified against source, per method.
