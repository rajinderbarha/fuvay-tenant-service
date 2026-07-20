# Test Report — Slice 2F-14A

## New tests

`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` — 30 tests, all passing:

- `TestJobNoteAccessControl` (10) — tenant owner/assigned technician allowed; unassigned
  technician, cross-tenant owner, customer denied; foreign job rejected; internal-note filtering
  for customer vs. staff reads; no mutation on denied calls.
- `TestJobMediaAccessControl` (7) — assigned technician allowed; foreign job, unassigned
  technician, cross-tenant, customer denied; no mutation on denied calls.
- `TestVoidJobOwnership` (3) — cross-tenant denied (with status-unchanged assertion), own-tenant
  and super_admin allowed.
- `TestRouterGuardSources` (6) — source-level verification that the router-level dependency
  upgrades are actually present (assessment routes, void_job, the 5 financial routes, and that
  `add_note`/`add_media` no longer accept a client `tenant_id`).
- `TestCanonicalCoverageRecount` (4) — direct, live recount against the CSV file itself: no
  duplicate rows, no false-positive rows, canonical totals (210/158), field_ops subtotal (40/29).

All fixtures are deterministic (`MagicMock`/`AsyncMock` job and DB objects with explicit
attribute values) — no test relies solely on source-string assertion for behavior (only
`TestRouterGuardSources` uses source inspection, and only to confirm which dependency is wired,
not to prove behavior — behavior is proven by the other 24 tests exercising the service directly).

## Regression

See regression-report.md — 192 passed in the slice-specific run; 1226 passed in the broad
partition sweep; 11 pre-existing live-environment exclusions honestly separated out and not
counted as passing.
