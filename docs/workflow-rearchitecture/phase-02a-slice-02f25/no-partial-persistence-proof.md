# No Partial Persistence Proof — Slice 2F-25

## Ordering

`flag_review`:
1. `_get_review_scoped` -> `NotFound` on foreign/missing/tenantless
2. already-flagged -> `CONFLICT`
3. status/reason/actor written
4. `_write_history` -> `db.add`
5. `_publish` event

`submit_reply`:
1. `_get_review_scoped` -> `NotFound`
2. existing reply -> `CONFLICT`
3. reply fields written
4. `_publish` event

`create_review_request`:
1. `_effective_tenant` -> `TENANT_ACCESS_DENIED` on mismatch/missing
2. row constructed and added

Every rejection precedes the first write in each path.

## Empirical proof

```
with pytest.raises(NotFoundException):
    await s.flag_review(uuid.uuid4(), "spam")
db.add.assert_not_called()
db.commit.assert_not_called()
```

and for the tenantless principal, `db.execute.assert_not_called()` — the guard
fires before a query is even issued.

## For every denied request

| Artifact | State |
|---|---|
| Review row | unchanged |
| `status` | unchanged |
| `flagged_reason` / `flagged_by` | unchanged |
| `tenant_reply` | unchanged |
| `ReviewStatusHistory` | no row |
| `ReviewRequest` | no row |
| Aggregate | unchanged (not reached by these paths at all) |
| Domain event | not published — `_publish` follows the writes |
| Commit | never reached |

## Transaction coherence
The service mutates ORM objects and adds history rows; the request-scoped
session commits on the success path only. A rejection leaves the session
uncommitted with no partial row.
