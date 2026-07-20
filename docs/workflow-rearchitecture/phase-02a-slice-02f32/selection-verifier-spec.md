# Selection Verifier Spec (WS11)

`scripts/workflow_rearchitecture/verify_selection_2f32.py` — 24 conditions
(W01–W24), each with a negative-fixture self-test.

| ID | Failure condition covered |
|---|---|
| W01 | Coverage is not 238/262 |
| W02 | Canonical unprotected count is not 24 |
| W03 | Live queue inventory doesn't exactly equal the canonical unprotected set |
| W04 | M01 sample route appears in the unprotected queue / loses protection |
| W05 | N01 sample route appears in the unprotected queue / loses protection |
| W06 | A protected route is included in the live queue inventory |
| W07 | Pending held count is not exactly 56 |
| W08 | The 3 N01 routes are not exactly resolved as added canonically |
| W09 | A canonically added N01 route remains labelled pending |
| W10 | A pending held route is counted canonically |
| W11 | Module counts do not sum to 24 |
| W12 | A route appears in multiple modules |
| W13 | Module membership doesn't match the live unprotected queue |
| W14 | No module is selected (Set A empty) |
| W15 | Set A routes span more than one module |
| W16 | Set A hash changed |
| W17 | Set B hash changed |
| W18 | Set C hash changed |
| W19 | The future contract omits a Set A route |
| W20 | The future contract includes a Set C route as implementation scope |
| W21 | The N01 integrity backlog is silently dropped |
| W22 | Canonical hash changed |
| W23 | Matrix hash changed |
| W24 | A doc falsely states that implementation was already done in this slice |

Run: `python scripts/workflow_rearchitecture/verify_selection_2f32.py`
(main) and `--selftest` (negative-fixture proof). Both must pass.
