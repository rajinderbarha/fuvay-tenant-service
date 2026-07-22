# Deferred Items — Slice 2F-25A

| Item | Reason deferred | Next step |
|---|---|---|
| Application-wide persona-based mutation sweep | Explicitly out of scope; the mission defers it to a later slice | The single highest-value next inventory action |
| Executed-exploit live integration tests for the legacy engine | This slice used deterministic doubles by design | Live E2E slice now that infrastructure is available |
| Public aggregate allow-list | Would invent public-review policy | Product decision #1 |
| Job-status gate on `create_request` | Would invent policy | Product decision #2 |
| Assignment-scoped technician access | Would invent policy | Product decision #4 |
| Filter hidden/rejected states from customer lists | Would invent policy | Product decision #5 |
| Re-derive `_recompute_aggregate` contribution rules | Not needed to scope the read | Bundle with the aggregate public decision |
| Retire/migrate the legacy engine | Carried from 2F-25 | Product decision #6 |
| Repair or retire the broken legacy reply contract | Carried from 2F-25 | Product decision #7 |
| Tenant-portal `resolve` control (403) | Carried from 2F-25 | Frontend/persona decision |
| Detecting silently-swallowed regressions | Node-ID comparison cannot see them | Consider failing loudly, or asserting on log output, in job-close paths |
| Slice-2D canaries | Explicitly prohibited | Requires `tenant-readonly-decision.md` conclusion |

## Remaining authorization queue
**7 modules / 17 routes** currently unprotected. No new module was begun.
