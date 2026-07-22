# Baseline Freeze — Slice 2F-39A

| Field | Value |
|---|---|
| Branch | `security/phase-2f39a-mounted-route-census` |
| Starting HEAD | `26b0109426aed9a8030932c8e8ea8d8927f8bcd3` (Slice 2F-39 final commit) |
| Worktree | `G:/serviceos-phase2f39a-route-census` |
| Working tree at start | clean |

## Environment (re-checked fresh)

Unchanged: no PostgreSQL, no Docker daemon, no Redis, no running app
server/worker.

## Starting position (inherited from Slice 2F-39, re-confirmed this slice)

- `PYTHONPATH=. python scripts/workflow_rearchitecture/list_routes.py` →
  `{"total_routes": 2320}` (unchanged)
- `inventory_mutation_routes.py` → 1,186 total auto-detected mutation
  routes, 261 `UNVERIFIED` (unchanged — no application route/guard code
  had changed between 2F-38 and the start of this slice, so this is
  expected, not merely assumed)
- 313/313 canonical, 0 unprotected (`verify_2f37.py` reconfirmed 21/21
  PASS at the start of this slice)
- Phase-2F: 2473 tests
- Full backend: 12,124 collected, 12,075 passed, 28 failed (2
  `test_sprint27_notifications.py` failures flagged authorization-adjacent
  — this slice's primary secondary deliverable)
