# Environment / Test Evidence

- Python 3.12.4, pytest 8.4.0, pluggy 1.6.0, anyio 4.14.1,
  pytest-asyncio 0.26.0 — unchanged from prior slices.
- No dependency added/removed/upgraded, no migration, no config change.
  Migration 144 remains unapplied (unchanged).
- PostgreSQL (`localhost:5432`) and Redis (`localhost:6379`) both accept
  TCP connections, but this slice's tests use the same static-inspection
  methodology as every prior slice in this program rather than live
  two-tenant database transactions — see
  [live-database-evidence.md](live-database-evidence.md) for the honest
  WS13 exclusion statement.
- Test run platform: Windows (win32), consistent with prior slices.
