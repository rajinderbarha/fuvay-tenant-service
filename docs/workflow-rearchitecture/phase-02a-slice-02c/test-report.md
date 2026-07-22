# Test Report — Slice 2C

## New tests this slice
`tests/test_phase2c_role_integrity.py` — 7 tests:
1. `test_detection_query_finds_a_freshly_inserted_invalid_role` — real-DB, self-contained (insert+rollback), proves migration 144's detection SQL works.
2. `test_detection_query_does_not_flag_any_canonical_role` — real-DB, proves no false positives against current live data.
3. `test_parse_mapping_rejects_non_canonical_role` — remediation script's `_parse_mapping` rejects `tenant_manager`/`platform_admin`.
4. `test_parse_mapping_accepts_all_10_canonical_roles` — parametrized across all 10.
5. `test_parse_mapping_rejects_malformed_entry` — malformed CLI args fail closed.
6. `test_tenant_engine_valid_roles_has_no_placeholder_aliases` — regression guard, `VALID_TENANT_ROLES` stays clean of all 6 known placeholder strings.
7. `test_auth_service_valid_platform_roles_are_exactly_the_5_platform_roles` — regression guard on the platform-role validator.

## Combined regression run

| Suite | Result |
|---|---|
| `tests/test_phase2a_my_work.py` | 13 passed |
| `tests/test_sprint21_execution.py` | 72 passed |
| `tests/test_customer_idor.py` | 6 passed |
| `tests/test_sprint4_tenant_onboarding.py` | 76 passed |
| `tests/test_phase11.py::test_create_review_requires_auth` | 1 passed |
| `tests/test_sprint24_customer_reviews.py` | 40 passed |
| `tests/test_phase2c_role_integrity.py` (new) | 7 passed |
| **Combined** | **260 passed, 0 failed** |

Same 14 pre-existing, unrelated `service_setup` duplicate-operation-ID warnings observed, unchanged, not fixed (documented in every prior slice's report).

## Live migration test (not a pytest, but a real, reproducible verification)
`alembic upgrade head` run live against the real database — confirmed to abort with the expected clear error naming both invalid accounts, and confirmed via `alembic current` (still 143) and a follow-up role-distribution query (unchanged) that zero schema or data change occurred.

## Live route-registration inspection
`scripts/workflow_rearchitecture/list_routes.py` run before and after this slice's changes: **2,322 total routes, unchanged** — no backend router/endpoint was added or modified this slice (the new script and migration are not FastAPI routes). No collisions.

## Frontend
No frontend code was changed this slice — no TypeScript compilation or lint run was needed (nothing to check).

## What was NOT tested
- A real `--apply --confirm` invocation of the remediation script against a real mapping — never executed, since no mapping was approved.
- Session-revocation behavior on remediation — not implemented this slice (see `token-session-impact.md`), so nothing to test yet.
- Whether other admin-facing role selectors beyond the ones already audited in Slices 2/2B exist and are correctly gated — the write-path audit (`role-write-path-audit.csv`) covers every path found, but a new, previously-unknown path could in principle exist outside the areas searched.
