# Test Report — Slice 2D

## New tests this slice
`tests/test_phase2d_tenant_access_model.py` — 18 tests across 5 classes:
1. `TestSeedScriptCanonicalGuard` (8 tests) — canonical-role set correctness, 6 parametrized invalid-role rejections (proven to occur before any DB call), valid-role acceptance.
2. `TestEffectiveAccessBaseStaffBundle` (5 tests) — direct `permission_checker.has()` calls proving what base `staff` grants/denies today, plus 2 regression guards on the override-wiring gap (one proving the mechanism works when fed data, one proving `get_current_user`'s source still never populates it — this second test is designed to *fail loudly* if a future change closes the gap, forcing `tenant-access-model.md` to be revisited rather than silently going stale).
3. `TestTenantMutationPermissionCoverage` (2 tests) — confirms the access_scope guard mechanism exists, and a regression-guard count proving its caller-file coverage remains exactly 2 (same fail-loudly-if-changed design).
4. `TestIntelligenceKBFieldNotAuthoritative` (1 test) — static source check that `kb_service.py` never treats `allowed_roles_json` as an authorization gate.
5. `TestRemediationScriptDisableFlag` (2 tests) — script version bump confirmed, `--disable`-without-`--mapping` CLI behavior exercised via subprocess.

## Combined regression run

| Suite | Result |
|---|---|
| `tests/test_phase2a_my_work.py` | 13 passed |
| `tests/test_sprint21_execution.py` | 72 passed |
| `tests/test_customer_idor.py` | 6 passed |
| `tests/test_sprint4_tenant_onboarding.py` | 76 passed |
| `tests/test_phase11.py::test_create_review_requires_auth` | 1 passed |
| `tests/test_sprint24_customer_reviews.py` | 40 passed |
| `tests/test_phase2c_role_integrity.py` | 7 passed |
| `tests/test_phase2d_tenant_access_model.py` (new) | 18 passed |
| **Combined** | **278 passed, 0 failed** |

Same 14 pre-existing, unrelated `service_setup` duplicate-operation-ID warnings, unchanged, not fixed (documented in every prior slice's report).

## Live actions this slice (beyond pytest)
- Ran the remediation script live 3+ times (default dry-run, targeted dry-run, targeted apply) against the real database.
- Ran `alembic upgrade head` live, twice (once before remediation confirming 2 blockers, once after confirming 1 blocker) — both correctly aborted with no schema change, confirmed via `alembic current`.
- Ran the new `check_role_integrity.py` script live, twice (default and `--detail`), confirming correct exit codes (1, since 1 invalid account remains).
- Did NOT run the hardened `canonical_seed_final_l5_01.py` live end-to-end, since it has its own destructive-reset safety gate (`ALLOW_DATABASE_RESET=true`) not overridden this slice — verified via static review and unit tests instead (see `known-limitations.md`).

## Route registration
`scripts/workflow_rearchitecture/list_routes.py` run after all changes: **2,322 total routes, unchanged** — no backend router/endpoint added or modified this slice. No collisions.

## Frontend
No frontend code was changed this slice — no TypeScript compilation or lint run needed.

## Workstream 4's "test representative actions" — partial coverage, honestly reported
The brief lists 16 specific actions to test (business profile read/update, staff list/invite, service read/update, pricing read/update, job read/assignment, quote read/approval, credit balance read/adjustment, settings read/update) across personas. This slice's tests cover a subset directly via `permission_checker.has()` (own-job read/update, settings read, staff-management denial) — proving the *mechanism* and its current gaps, not a full per-action HTTP-level test matrix across all 16 actions × both proposed personas. A full matrix would require live `TestClient` calls with real authentication for each of the 16 actions, which is a substantially larger test-authoring effort than this slice's remaining budget supported, especially since two of the three personas being tested (manager, read-only) are *known blocked* — testing them exhaustively would mostly produce "correctly denied" results already explained by the architecture findings, not new information.
