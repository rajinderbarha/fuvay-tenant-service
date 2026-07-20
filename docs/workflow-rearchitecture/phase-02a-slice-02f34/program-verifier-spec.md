# Program Verifier Spec (WS14)

`scripts/workflow_rearchitecture/verify_program_2f34.py` — 24 conditions
(P01–P24), each with a negative-fixture self-test.

| ID | Failure condition covered |
|---|---|
| P01 | Coverage is not the accepted post-2F-33 position (241/264) |
| P02 | Canonical queue is not exactly 23 |
| P03 | Live queue inventory doesn't match the canonical unprotected set |
| P04 | Pending held count is not reconciled (not 54) |
| P05 | A pending held route is counted canonically |
| P06 | An M01 route reappears in the queue |
| P07 | An N01 route reappears in the queue |
| P08 | A closed geo Set A/B route reappears in the queue |
| P09 | Module route counts do not sum to 23 |
| P10 | A route appears in multiple remaining modules |
| P11 | A module remains UNKNOWN |
| P12 | A canonical route is not assigned to a future slice |
| P13 | A pending held route is not assigned or disposed |
| P14 | A route appears in multiple future slices |
| P15 | A/B/C hashes are missing for a future slice |
| P16 | A module/slice lacks a separate implementation contract |
| P17 | N01 integrity backlog disappears |
| P18 | Migration 144 is scheduled before readiness proof |
| P19 | readonly@ remediation is scheduled before final enforcement |
| P20 | Canonical hash changed |
| P21 | Matrix hash changed |
| P22 | Held registry hash changed (i.e. it was modified, which must never happen) |
| P23 | Documentation claims implementation occurred this slice |
| P24 | More or fewer than four future slices are frozen |

Run: `python scripts/workflow_rearchitecture/verify_program_2f34.py`
(main) and `--selftest` (negative-fixture proof). Both must pass.
