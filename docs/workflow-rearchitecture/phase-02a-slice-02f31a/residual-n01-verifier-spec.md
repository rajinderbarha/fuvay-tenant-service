# Residual N01 Verifier Spec (WS13)

`scripts/workflow_rearchitecture/verify_n01_2f31a.py` — 21 conditions
(R01–R21), each with a negative-fixture self-test
(`--selftest`, verified to fire when the corresponding state is forced
false).

| ID | Failure condition covered |
|---|---|
| R01 | Scope drift — one of the 5 residual routes not canonical/VERIFIED |
| R02 | Denominator changed |
| R03 | Protected count wrong (not 238) |
| R04 | Unprotected count wrong (not 24) |
| R05 | M01/protected-route regression (sample M01 route lost VERIFIED) |
| R06 | Out-of-scope route change (GET media route added to mutation inventory) |
| R07 | Historical evidence rewrite (2F-21 artifact) |
| R08 | Historical evidence rewrite (2F-23 artifact) |
| R09 | Admitted-role narrowing on the scope-only guard |
| R10 | Missing mutation scope enforcement |
| R11 | Client tenant widening (trusted-tenant check missing/skipped) |
| R12 | Untrusted MediaService tenant authority (constructor doesn't accept it) |
| R13 | Unguarded direct service call bypassing the router |
| R14 | Object-ID-only authorization (assert_can_delete no longer delegates to assert_can_view) |
| R15 | Foreign/missing object oracle |
| R16 | Client-authoritative storage key (raw file_name reaches the key) |
| R17 | Token/key leakage (cloudinary secret logged) |
| R18 | Falsely-claimed-closed destructive inconsistency |
| R19 | Coverage arithmetic inconsistency |
| R20 | Canonical hash mismatch (unexpected additional edit) |
| R21 | False application-wide-closure claim in a slice doc |

Run: `python scripts/workflow_rearchitecture/verify_n01_2f31a.py` (main) and
`--selftest` (negative-fixture proof). Both must pass for closure to stand.
