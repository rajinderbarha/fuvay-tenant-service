# Slice 2F-35 Verifier Spec (WS18)

`scripts/workflow_rearchitecture/verify_2f35.py` — 22 conditions
(R01–R22), each with a negative-fixture self-test.

| ID | Failure condition covered |
|---|---|
| R01 | Frozen A/B/C scope or hashes drift |
| R02 | A Set B route remains unadjudicated |
| R03 | A Set C route was newly protected (changed by this slice) |
| R04 | The canonical Set A routes remain unprotected |
| R05 | An included mutation lacks mutation-scope enforcement |
| R06 | delete_endpoint mutates by ID without a tenant predicate |
| R07 | RAG KB lookup for closed methods lacks tenant scoping |
| R08 | Client tenant widens rotate_api_key authority |
| R09 | Client tenant widens generate_document authority |
| R10 | A service accepts missing/untrusted tenant context |
| R11 | Foreign objects create an information oracle |
| R12 | An alternate-route bypass remains |
| R13 | The field_ops internal caller was not updated (would fail closed) |
| R14 | Aggregate coverage arithmetic is inconsistent |
| R15 | Unprotected count is inconsistent |
| R16 | M01 regresses |
| R17 | N01 regresses |
| R18 | Geo regresses |
| R19 | A Slice 2F-36/37 application file changed |
| R20 | Documentation claims application-wide closure |
| R21 | Canonical hash changed unexpectedly |
| R22 | Matrix hash changed unexpectedly |

Run: `python scripts/workflow_rearchitecture/verify_2f35.py` (main) and
`--selftest` (negative-fixture proof). Both must pass.
