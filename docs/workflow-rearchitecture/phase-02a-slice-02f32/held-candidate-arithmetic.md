# Held-Candidate Arithmetic (WS2)

## Reconciliation, from route keys (not prose)

Source of truth: `docs/workflow-rearchitecture/phase-02a-slice-02f27a/
unauthorized-candidate-hold-registry.csv` — 59 data rows, all originally
`PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION`.

Three route keys match the N01 Set B routes Slice 2F-31 adjudicated and
added canonically (confirmed by exact `(method, path)` match, not by
counting or by trusting a prose claim):

```
POST   /v1/media/upload/initiate
POST   /v1/media/upload/{session_id}/confirm
DELETE /v1/media/tenants/{tenant_id}/files/{file_id}
```

All three are canonical and `VERIFIED` as of the current canonical CSV
(hash `1f7891798eb8382f`) — confirmed directly, not assumed.

```
59 total held candidates
 - 3 resolved (RESOLVED_ADDED_CANONICALLY, route-key exact match to N01 Set B)
= 56 pending (PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION)
```

**56 matches the mission's expected pending count exactly**, derived here
by route-key set subtraction against the live canonical CSV, not accepted
as a prose figure.

## Proof: no canonically-added route remains labelled pending

All 3 resolved rows were re-checked against the current canonical CSV and
found `VERIFIED` (not merely present). No route among the 56 remaining
pending rows is canonical (spot-checked: none of the 56 route keys appear
in the canonical CSV at all — they remain, by definition of "held",
entirely absent from coverage and the matrix).

Full row-level detail: [held-candidate-status-reconciliation.csv](held-candidate-status-reconciliation.csv).
