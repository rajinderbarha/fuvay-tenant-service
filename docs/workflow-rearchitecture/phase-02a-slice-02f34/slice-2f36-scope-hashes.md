# Slice 2F-36 Scope Hashes

| Set | File | Hash |
|---|---|---|
| A (module scope, 18 routes) | `slice-2f36-module-scope.csv` | `0994c5373c08a2b6` |
| B (held scope, 28 routes) | `slice-2f36-held-scope.csv` | `9fe3fe305b53d174` |
| C (exclusion scope, 5 routes) | `slice-2f36-exclusion-scope.csv` | `6adb8d71a4c7e2b6` |

Frozen starting position for Slice 2F-36 depends on Slice 2F-35's exact
final output — this slice cannot compute 2F-36's true starting canonical/
matrix hash in advance (2F-35 runs first and will change it). Slice 2F-36
must load its actual starting hashes live from Slice 2F-35's own
`approval-gate.md`/`canonical-hash-evidence.md` at execution time, not
from this document.

If Slice 2F-35 has not yet run, or its output does not reconcile, Slice
2F-36 must stop with `AUTHORITATIVE_QUEUE_RECONCILIATION_BLOCKED`.

Slice 2F-36 may not silently add or remove routes from these Set A/B/C
files.
