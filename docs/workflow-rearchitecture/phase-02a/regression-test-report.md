# Regression Test Report

## Backend

| Suite | Result |
|---|---|
| `tests/test_phase2a_my_work.py` (new) | 13 passed |
| `tests/test_sprint21_execution.py` (pre-existing, same engine touched) | 72 passed |
| **Combined** | **85 passed, 0 failed** |

Command run: `PYTHONPATH=. python -m pytest tests/test_phase2a_my_work.py tests/test_sprint21_execution.py -q`

### Pre-existing, unrelated warnings observed (not introduced by this phase)
14 `UserWarning: Duplicate Operation ID ...` warnings from `app/engines/service_setup/templates_router.py` (duplicate FastAPI operation IDs for `list_templates`, `create_template`, `get_template`, `update_template`, `publish_template`, `archive_template`, `delete_template`). These are pre-existing (confirmed present before this phase's changes — they originate from the `service_setup` vs `admin_catalog` duplicate-template-engine issue already flagged in Phase 1A's `backend-blockers.md` item 5) and are reported here per the "do not hide unrelated pre-existing failures" rule, not fixed (out of scope).

## Frontend
Ran TypeScript type checking (`npx tsc --noEmit`) on `frontend/tenant-portal` after all changes:

- **Result: 0 errors, exit code 0.**

No `next lint` or `next build` was run this phase (not requested as a gate item beyond type-checking + the honesty requirement to report what was/wasn't run; both would be reasonable follow-ups before deploying).

## Full backend suite
The complete repository-wide pytest suite was **not** run this phase (large, slow, and the changes are isolated to one new file + one new router registration + two content-only page edits with no shared-module changes) — only the directly-relevant and immediately-adjacent suites above were run. This is a scope decision, not a hidden failure: no test outside the two files above was executed.
