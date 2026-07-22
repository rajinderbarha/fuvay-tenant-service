# Baseline Freeze — Slice 2F-39

| Field | Value |
|---|---|
| Branch | `security/phase-2f39-certification-remediation` |
| Starting HEAD | `ba01d15b3188c1eaeb5a11a981a51e0886c722ae` (Slice 2F-38 final commit) |
| Worktree | `G:/serviceos-phase2f39-remediation` |
| Working tree at start | clean (0 porcelain, excluding this slice's own new guard script) |

## Environment (re-checked fresh)

Unchanged from every prior slice: no `psql`/`pg_ctl`/`postgres` in PATH, no
`DATABASE_URL`/`POSTGRES*`/`REDIS*` env vars, Docker daemon unreachable
(client present, server not running). No PostgreSQL runtime evidence is
possible in this environment.

## Starting position (inherited from Slice 2F-38, re-confirmed this slice)

- Canonical protected: 313/313, unprotected 0 (`verify_2f37.py` reconfirmed
  21/21 PASS at the start of this slice, before any fix)
- Phase-2F baseline: 2445 tests
- Full backend baseline: 12,096 collected, 12,030 passed, 45 failed, 21
  skipped
- Both demo accounts: `MANUAL_ROLE_CONFIRMATION_REQUIRED`
- Migration 144: unapplied, unproven in PostgreSQL
- Unresolved mutation-like routes: ~261 (2F-38's figure, not yet
  independently reproduced this slice — see `route-census-reproduction.md`)
