# Slice 2F-37 Verifier Spec

`scripts/workflow_rearchitecture/verify_2f37.py` — 21 conditions
(R01-R21), each with a `--selftest` negative fixture.

| ID | Condition |
|---|---|
| R01 | Set A/B/C frozen hashes unchanged |
| R02 | every Set A route is present and protected |
| R03 | all 17 Set B routes received a final disposition |
| R04 | every canonically-added Set B route is protected |
| R05 | all 19 routes (3 Set A + 16 Set B) have a live access-scope guard |
| R06 | every touched service has a `_require_trusted_tenant` helper |
| R07 | zone update/delete check tenant ownership (previously zero scoping) |
| R08 | rule update/delete check tenant ownership (previously zero scoping) |
| R09 | commerce initiate_purchase/recalculate_badges call the deposit ownership check |
| R10 | warranty claim verifies parent job tenant/customer ownership |
| R11 | compliance deletion/portability requests are self-only |
| R12 | recalculate_badges no longer guarded by a read permission |
| R13 | coverage arithmetic is 313/313 |
| R14 | unprotected count is 0 |
| R15 | M01/geo/2F-35/2F-36 sample routes remain VERIFIED (no regression) |
| R16 | no Set C route was newly protected by this slice |
| R17 | no N01 media file carries a 2F-37 marker (frozen, not remediated) |
| R18 | no document claims application-wide closure/certification |
| R19-R20 | canonical/matrix hash match the post-closure frozen value |
| R21 | N01 final status honestly documents `IMPLEMENTATION_SCOPE_BLOCKED` |

Run: `python scripts/workflow_rearchitecture/verify_2f37.py` /
`--selftest`.
