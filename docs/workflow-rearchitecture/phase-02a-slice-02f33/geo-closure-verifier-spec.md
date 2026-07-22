# Geo-Zone Closure Verifier Spec (WS16)

`scripts/workflow_rearchitecture/verify_geo_2f33.py` — 22 conditions
(G01–G22), each with a negative-fixture self-test.

| ID | Failure condition covered |
|---|---|
| G01 | A/B/C scope hashes changed unexpectedly |
| G02 | A Set B route remains unadjudicated |
| G03 | A Set C route was added to canonical coverage |
| G04 | The canonical delete route remains unprotected |
| G05 | delete_zone lacks mutation access-scope enforcement |
| G06 | Zone mutation occurs by ID without tenant scope |
| G07 | Client tenant widens create_zone authority |
| G08 | GeoService accepts missing/untrusted tenant context |
| G09 | A foreign object creates an information oracle |
| G10 | Parent geography ownership evidence missing/undocumented |
| G11 | Cross-tenant reparenting audit missing |
| G12 | An alternate route bypass remains |
| G13 | create_zone lacks a canonical row |
| G14 | update_location lacks a canonical row |
| G15 | Coverage arithmetic inconsistent (not 241/264) |
| G16 | Unprotected count inconsistent (not 23) |
| G17 | M01 regresses |
| G18 | N01 regresses |
| G19 | Documentation claims application-wide closure |
| G20 | Canonical hash unexpectedly changed |
| G21 | Matrix hash unexpectedly changed |
| G22 | update_location's scope guard loses the read-only rejection |

Run: `python scripts/workflow_rearchitecture/verify_geo_2f33.py` (main)
and `--selftest` (negative-fixture proof). Both must pass.
