# Slice 2F-37 Scope Hashes

| Set | File | Hash |
|---|---|---|
| A (module scope, 3 routes) | `slice-2f37-module-scope.csv` | `6d64894af41dbf67` |
| B (held scope, 17 routes) | `slice-2f37-held-scope.csv` | `b4bf520b7764f11b` |
| C (exclusion scope, 20 routes) | `slice-2f37-exclusion-scope.csv` | `2074bf7001bc1d27` |

Frozen starting position for Slice 2F-37 depends on Slice 2F-36's exact
final output — must be loaded live at execution time, not assumed. If
Slice 2F-36 has not run or its output does not reconcile, Slice 2F-37
must stop with `AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED`.

Slice 2F-37 may not silently add or remove routes from these sets, and
must keep the N01 domain-integrity sub-scope
([n01-domain-integrity-scope.md](n01-domain-integrity-scope.md))
separate from canonical-coverage arithmetic.
