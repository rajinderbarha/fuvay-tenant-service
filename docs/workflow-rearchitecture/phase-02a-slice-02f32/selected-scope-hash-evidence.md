# Selected Scope Hash Evidence (WS9 Freeze)

| File | Hash (sha256, first 16 hex) |
|---|---|
| `selected-canonical-route-scope.csv` (Set A — 1 route) | `fc45fa777f47c2c9` |
| `selected-held-adjudication-scope.csv` (Set B — 2 routes) | `593837fac1076324` |
| `selected-out-of-scope-adjacent-routes.csv` (Set C — 24 rows: 23 canonical + 1 observation) | `578a7e506b83dc09` |
| `authoritative-unprotected-route-inventory.csv` (full 24-route live queue) | `84869431deef0533` |
| `held-candidate-status-reconciliation.csv` (59-row full held registry reconciliation) | `0e861c319cd1fc37` |

Canonical/matrix hashes (unchanged by this slice):

- Canonical: `1f7891798eb8382f`
- Matrix: `abac4ae72e8ab1d4`

The future implementation slice may not silently add or remove routes from
Set A, Set B, or Set C — any change requires re-freezing and re-hashing
these exact files.
