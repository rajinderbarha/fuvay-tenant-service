# Phase 3D — Test Results

## Backend command

```bash
python -m pytest tests/ -q
```

## Backend result

**8046 passed, 37 failed, 1 skipped** (8084 collected, 411s). All 37
failures are the exact same pre-existing, unrelated baseline confirmed in
every prior sprint this session (frontend-assertion tests predating a
concurrent process's nav-config refactor: `test_sprint34c_master_data.py`,
`test_sprint38_universal_catalog.py`, and others documented identically in
`PHASE_3B_BACKEND_TEST_RESULTS.md`). **0 new failures.**

## Frontend TypeScript result

```bash
npx tsc --noEmit
```

**0 errors.**

## Frontend lint result

`npm run lint` → pre-existing broken (`next lint` subcommand removed in
Next.js 16), documented in every prior sprint, not caused by Phase 3.

## Frontend test result

No `npm test` script exists in `package.json` (only `dev`/`build`/`start`/
`lint`). Python static-inspection tests remain the established substitute:
`test_phase3_pricing_rules_certification.py` (18), `test_phase3b_backend_
routing_certification.py` (21), `test_phase3c_frontend_certification.py`
(24) — **63/63 passing**, re-confirmed this sprint.

## Known pre-existing failures

37 backend tests (nav-config/frontend-assertion tests for unrelated pages),
`next lint` broken, `next build` static-export fails on one unrelated
pre-existing page (`/admin/refund-requests`).

## New failures caused by Phase 3 (3A/3B/3C/3D combined)

**None.**

## Result: **PASS — no new regressions across the full Phase 3 body of work.**
