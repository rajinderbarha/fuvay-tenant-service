# Canonical Queue Reconciliation - Slice 2F-28

Source of truth: `tenant-mutation-endpoint-inventory.csv` (hash
`e7a89231207221aa`), 259 rows.

- Protected (guard_status in the VERIFIED set): **214**
- Unprotected: **45**
- 214 + 45 = 259 (exact)

Proven by the verifier (S01-S06):
- Exactly 45 canonical unprotected routes exist.
- The exported queue equals that set (no missing, no extra).
- No protected route appears in the queue.
- No held candidate appears in the canonical set.
- Every queued route maps to exactly one canonical inventory row.

Unprotected guard-status breakdown:
| guard_status | count |
|---|---|
| AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | 20 |
| ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE | 13 |
| PERMISSION_ONLY_NOT_SCOPE_AWARE | 12 |
| **Total** | **45** |
