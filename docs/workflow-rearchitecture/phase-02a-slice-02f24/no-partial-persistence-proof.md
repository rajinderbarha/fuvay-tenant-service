# No Partial Persistence Proof — Slice 2F-24

## Structural argument

In both mutating service methods every rejection occurs **before** the first
`db.add()`.

`flag_review` order:
1. actor-type allow-list -> `PERMISSION_DENIED`
2. scope presence check -> `PERMISSION_DENIED` (before any query)
3. scoped ownership lookup -> `REVIEW_NOT_FOUND`
4. reason-code normalisation
5. `db.add(flag)`  <- first write
6. `review.status = STATUS_FLAGGED`
7. `flush` -> `_log_event` -> `commit`

`submit_reply` order:
1. scoped ownership lookup -> `REVIEW_NOT_FOUND`
2. duplicate-reply check -> `REPLY_ALREADY_EXISTS`
3. policy read
4. `db.add(reply)`  <- first write
5. `flush` -> `_log_event` -> optional notify -> `commit`

Schema rejections (unknown field, bad `reason_code`, empty `reply_text`) occur
during FastAPI validation, before the handler is entered at all.

Asserted by `test_ownership_check_precedes_any_write_in_flag` and
`..._in_reply`, which compare source positions of the lookup and `db.add`.

## Empirical proof

The denial tests use a session double and assert the negative directly:

```
db.add.assert_not_called()
db.flush.assert_not_called()
db.commit.assert_not_called()
```

and the no-scope test additionally asserts `db.execute.assert_not_called()` --
the guard fires before a query is even issued.

## For every denied or invalid request

| Artifact | State after denial |
|---|---|
| Review status | unchanged |
| Existing reply | unchanged |
| New reply | none created |
| Flag record | none created |
| Moderation record | none |
| Rating aggregate | unchanged (not reachable from these paths at all) |
| Notification | none -- emitted only after successful persistence |
| Audit / domain success event | none -- `_log_event` runs after `db.add`/`flush` |
| Commit | never reached |
| Pre-existing state | unchanged |

## Transaction coherence
Each service method owns its transaction (`flush` then `commit`) and commits
only on the success path. A failure anywhere before the commit leaves the
session uncommitted with no partial row.
