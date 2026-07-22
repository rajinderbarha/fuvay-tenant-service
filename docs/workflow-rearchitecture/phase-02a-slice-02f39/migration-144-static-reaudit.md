# Migration 144 Static Reaudit — Slice 2F-39

`alembic/versions/144_users_role_canonical_check.py` hash unchanged
(`824c4ed2...13c8a`, matches 2F-38's recorded value) — this slice made no
change to the migration itself, consistent with the frozen contract
("Do not edit it merely to force successful execution").

Re-verified after this slice's seed hardening:

| Property | Finding |
|---|---|
| Predecessor/upgrade/downgrade | Unchanged from 2F-38's audit — safe, fail-closed, schema-only |
| Unknown-role behavior | Fails closed (raises, refuses to apply) — unchanged |
| No privilege-increasing default | Confirmed — the migration only ever restricts, never grants |
| No ambiguous demo mapping | Confirmed — the migration does not attempt to resolve `manager@`/`readonly@`'s roles itself; it would correctly refuse to apply against a database containing either in their current invalid state |
| Seed compatibility (new this slice) | Both fixed seed scripts now fail closed on invalid roles *before* the migration would ever need to reject anything at the database level — defense in depth, not a replacement for the migration's own database-level check |
| Large-table/locking risk | Unchanged, unmeasured open finding from 2F-38 (`ACCESS EXCLUSIVE` lock during CHECK validation, not measured against real table size) |

## Verdict

Static audit remains **PASS with the one open large-table-lock finding**,
now additionally supported by two independently-hardened application-level
seed guards. Runtime proof remains blocked — see
`postgres-environment-evidence.md`.
