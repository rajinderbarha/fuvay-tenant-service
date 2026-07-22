# Post-M01 Queue Reconciliation - Slice 2F-30

Rebuilt directly from `tenant-mutation-endpoint-inventory.csv`
(`fbe7cf863afa0d84`), **not** from the 2F-28 45-route artifact.

- Rows: 259. Protected: 226. Unprotected: **33**. 226 + 33 = 259.
- All 33 resolve to a mounted route (checked against the live route index).
- Each appears exactly once and maps to exactly one canonical row.
- **No M01 route appears**; all 12 M01 routes are still protected.
- No held candidate is counted.

Reconciliation against 2F-28: `45 (2F-28 queue) - 12 (M01 closed) = 33`.

Unprotected by guard status:

| guard_status | count |
|---|---|
| AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | 8 |
| ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | 13 |
| PERMISSION_ONLY_NOT_SCOPE_AWARE | 12 |
| **Total** | **33** |
