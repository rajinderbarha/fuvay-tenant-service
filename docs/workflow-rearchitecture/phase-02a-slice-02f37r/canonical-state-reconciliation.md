# Canonical State Reconciliation

Independently recomputed from the committed `security/phase-2f-authorization-recovered`
branch (commit `532190d`), via `verify_2f37.py`'s live `route_index()` /
`route_guards()` introspection against the actual running FastAPI app
object — not by reading the preserved documentation's claimed numbers.

| Metric | Recomputed | Previously claimed (2F-37 docs) | Match |
|---|---|---|---|
| Canonical denominator | 313 (R19/R20 hash match) | 313 | Yes |
| Protected | 313 (R13) | 313 | Yes |
| Unprotected | 0 (R14) | 0 | Yes |
| Set A/B/C frozen hashes | unchanged (R01) | unchanged | Yes |
| Canonical hash | matches frozen post-closure value (R19) | — | Yes |
| Matrix hash | matches frozen post-closure value (R20) | — | Yes |

`verify_2f37.py` itself performs this recomputation (it is not a static
assertion against a stored number — R01/R19/R20 explicitly diff live
introspected hashes against the frozen values), so this table reports the
verifier's actual re-derived result, not a copy of prior documentation.

Held-registry, Set C, and product-decision-registry recomputation were not
independently re-derived from a from-scratch reconciliation script in this
slice (no such script exists in `scripts/workflow_rearchitecture/`); this
slice relies on `verify_2f37.py`'s R01/R03/R16 conditions (Set A/B/C hash
match, all 17 Set B routes dispositioned, no Set C route newly protected)
as the available independent evidence for those dimensions. A dedicated
from-scratch held/Set-C recount script is noted as a gap in
`known-limitations.md`.
