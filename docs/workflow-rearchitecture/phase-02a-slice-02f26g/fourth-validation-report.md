# Fourth Holdout Validation Report — Slice 2F-26G

## Result: 23/24 all-field agreement. Required 24/24. **Gate fails.**

| Field | Agreement |
|---|---|
| Persona | **24/24** |
| Tenant direction | **24/24** |
| Capability family | **24/24** |
| Side effect | **24/24** |
| Abstention reason | **24/24** |
| Capability action | 23/24 |
| **All six** | **23/24** |

Across four independent holdouts: **4/24 → 19/24 → 21/24 → 23/24**.

D-01 through D-08 all hold on a fresh, disjoint, blinded sample. The two
defects this slice targeted are gone: capability family is 24/24 (D-07) and
side effect is 24/24 (D-08). The single remaining miss is a **new** defect in
the capability-action layer.

## Freeze ordering

| Artifact | Hash |
|---|---|
| Eligible population (51) | `67a4a51614489bd8` |
| Holdout manifest | `5a835bcc011e90a1` |
| Manual verdicts | `708a9aaa5a21d00c` |
| Evidence review | `85a64b8c76d5631c` |
| Family rules at freeze | `c05e7fdd3c773ff4` |
| Write detector at freeze | `c60e15c855c9e992` |

Manifest, manual verdicts and evidence review all frozen before the classifier
ran. All asserted in tests; family-rule and write-detector hashes are also
asserted unchanged by verifier fixtures F01/F02.

## The single disagreement — D-09 (new)

`POST /v1/tenants/{tenant_id}/engines/bulk-disable`

- Manual capability action: **deactivate**
- Tool capability action: **create**

The action-token table matches `/disable\b`, which requires a slash before
`disable`. The path segment is `bulk-disable`, so `/disable` does not match,
and the route fell through to the POST default `create`. The manual verdict is
correct: disabling engines is a `deactivate` action.

This is the same class of gap as D-07 — a pattern too literal for a
real-world path shape — but in the action layer rather than the family layer.
It is registered as **D-09** for the next slice.

## Why nothing was fixed

D-09 was found by the holdout that measures the classifier. Repairing it and
re-running this holdout would be the circular proof the mission forbids. This
holdout is now burned; D-09's repair must be validated against a fifth,
newly frozen holdout.

## Abstention contract

Manual abstained on 6 routes; the tool abstained on exactly the same 6, with
matching `OWNERSHIP_CHECK_IN_SERVICE_NOT_TRACEABLE` reason codes. Zero
avoidable abstentions. No abstained route contributes to any canonical
decision.

The six were confirmed by the WS11 evidence-review checklist to have ownership
predicates in the service layer that are not traceable from the handler
(`media/{media_id}`, `media/upload/confirm`, `appointments/confirm`,
`dispatch/accept`, `rag/knowledge-bases`, `media/signed`), so abstention is the
correct outcome rather than a guess.

## Consequence

Zero canonical edits. Canonical `45244cd9540456db` and matrix
`4c7c3bce02096a43` preserved. **GLOBAL_COVERAGE_RECONCILIATION_BLOCKED.**
