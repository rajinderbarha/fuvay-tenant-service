# Slice 2F-36 Verifier Spec

`scripts/workflow_rearchitecture/verify_2f36.py` — 23 conditions (R01-R23,
including R18b), each with a `--selftest` negative fixture.

| ID | Condition |
|---|---|
| R01 | Set A/B/C frozen hashes unchanged |
| R02 | every Set A route is present and protected |
| R03 | all 28 Set B routes received a final disposition |
| R04 | every canonically-added Set B route is protected |
| R05 | all 42 routes (18 Set A + 24 Set B) have a live access-scope guard |
| R06 | `set_default` re-checks `owner_user_id` before mutating `is_default` |
| R07 | every touched service has a `_require_trusted_tenant` helper |
| R08 | every `_require_trusted_tenant` rejects missing tenant context |
| R09 | appointment ownership check is non-oracular |
| R10 | `dispatch_job` cross-checks the job's own tenant before advancing it |
| R11 | catalog `update_item` checks tenant ownership before mutating |
| R12 | reservation confirm/release predicate the lookup by `tenant_id` |
| R13 | every touched router passes `actor_tenant_id` into its service |
| R14 | coverage arithmetic is 294/297 |
| R15 | unprotected count is 3 |
| R16-R18b | M01/N01/geo/2F-35 sample routes remain VERIFIED (no regression) |
| R19 | no Set C route was newly protected by this slice |
| R20 | no Slice 2F-35/37-exclusive application file carries a 2F-36 marker |
| R21 | no document claims application-wide closure |
| R22-R23 | canonical/matrix hash match the post-closure frozen value |

Run: `python scripts/workflow_rearchitecture/verify_2f36.py` /
`--selftest`.
