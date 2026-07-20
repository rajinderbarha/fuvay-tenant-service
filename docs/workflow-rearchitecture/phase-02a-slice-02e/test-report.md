# Test Report — Slice 2E

## New tests this slice
`tests/test_phase2e_effective_permissions.py` — 9 tests across 4 classes:
1. `TestFullRoundTripPermissionOverrides` (3) — proves the JWT-payload → `UserContext` → `PermissionChecker` round trip actually changes authorization outcomes (grant beyond base bundle, deny overriding base bundle grant, full payload simulation).
2. `TestManagerPersonaBackendPipelineAlreadyExists` (2) — confirms `invite_staff`/`update_permissions`' pre-existing source still contains the expected `StaffPermission(...)` creation and tenant-ownership check.
3. `TestMutationGuardCoverageSurvey` (2) — regression-guards the router-file-level survey's exact finding (16 files exist, exactly 1 uses the read-only guard) so any future change is caught and the corresponding docs revisited.
4. `TestAuthorizationIntegrityScript` (2) — confirms the extended integrity script's permission-registry loading and canonical-role set.

## Corrected test from Slice 2D
`tests/test_phase2d_tenant_access_model.py::TestEffectiveAccessBaseStaffBundle::test_get_current_user_source_still_never_sets_permission_overrides` was **intentionally designed to fail** the moment the wiring gap closed — it did, correctly, this slice. Renamed to `test_get_current_user_now_populates_permission_overrides` and flipped to assert the fix is present and stays present.

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
| `tests/test_phase2d_tenant_access_model.py` (1 test corrected) | 18 passed |
| `tests/test_phase2e_effective_permissions.py` (new) | 9 passed |
| **Combined** | **287 passed, 0 failed** |

Same 14 pre-existing, unrelated `service_setup` duplicate-operation-ID warnings, unchanged.

## Highest-risk change this slice, proven safe
The one-line fix to `app/dependencies/auth.py::get_current_user` touches the single most central, most-executed code path in the entire backend (every authenticated request calls this function). The full 287-test combined regression suite passing after this change is the primary evidence it introduces no regression. A broader, full-repository `pytest tests/` run was attempted but not completed within this session's time budget (the suite is large — thousands of tests; a 100-second partial run reached ~5% with zero failures before being time-boxed) — see `known-limitations.md`.

## Live actions this slice (beyond pytest)
- Ran `check_role_integrity.py --detail` live, confirming all new checks return 0 except the known 1 invalid role.
- Did not run `alembic upgrade head` again (no state change since Slice 2D's last attempt, no new information to gain).
- Did not run the remediation script in apply mode (no remediation was performed this slice).

## Route registration
`scripts/workflow_rearchitecture/list_routes.py`: 2,322 total routes, unchanged. This slice touched only `app/dependencies/auth.py` (the one-line fix) and 2 scripts (`remediate_invalid_roles.py`'s docstring context unchanged in behavior, `check_role_integrity.py` extended) — no FastAPI router or endpoint was added or modified. No collisions.

## Frontend
No frontend code was changed this slice — no TypeScript compilation or lint run needed.
