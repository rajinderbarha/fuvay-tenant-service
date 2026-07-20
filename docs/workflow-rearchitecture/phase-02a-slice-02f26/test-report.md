# Test Report — Slice 2F-26

## New suite
`tests/test_phase2f26_application_wide_inventory.py` — **42 passed**

Breakdown and anti-vacuity notes: `deterministic-test-report.md`.

## Verifier
`scripts/workflow_rearchitecture/verify_app_wide.py` — 16 checks, **exit 0**,
with 4 negative fixtures proving it can fail.

## Recount suites
`test_phase2f14a`, `2f17a`, `2f19`, `2f21`, `2f23`, `2f25`, `2f25a` —
**202 passed** after the 257/214 update.

## Full repository
Run twice under a stable environment after all writes completed — see
`regression-report.md` for exact node-ID comparison.

## Reporting breakdown

| Category | Count |
|---|---|
| **Failures attributable to this slice** | **0** |
| **Errors attributable to this slice** | **0** |
| Environment | API + PostgreSQL + Redis reachable throughout |

## Self-corrections during authoring
1. Four tooling bugs fixed before any result was trusted (empty route walk,
   prefix-based persona, audit/external marker overlap, cross-engine name
   collision) plus a path-form normalization fix.
2. A bulk edit to the recount assertions broke indentation in seven test files;
   caught by collection errors and repaired.
3. My own baseline run was invalidated by a concurrent write; discarded rather
   than used.
