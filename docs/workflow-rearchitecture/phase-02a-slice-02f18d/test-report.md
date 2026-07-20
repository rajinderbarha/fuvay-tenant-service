# Test Report

| Suite | Result |
|---|---|
| `tests/test_phase2f18d_platform_notifications_first_use_and_claim_integrity.py` (new) | 12 passed |
| `tests/test_phase2f18c_platform_notifications_media_sharing_retrieval.py` (mocks updated for FOR UPDATE + 1 test renamed) | 11 passed |
| `tests/test_phase2f18b_platform_notifications_media_authority.py` (mocks updated for FOR UPDATE + 1 test rewritten to reflect the corrected technician policy) | 9 passed |
| `tests/test_phase2f18a_platform_notifications_technician_privacy.py` (mocks updated for FOR UPDATE) | 26 passed |
| `tests/test_phase2f18_platform_notifications_authorization.py` (unchanged) | 49 passed |
| `tests/test_sprint27_notifications.py` (unchanged) | all mocked tests pass |
| `tests/test_module_l5_19_staff_chat.py` | mocked portion passes; `*Live*` excluded |
| `tests/test_module_l5_20_chat_notify.py` | mocked portion passes; `*Live*` excluded |
| `tests/test_module_l5_14_chat.py` | mocked portion passes; `*Live*` excluded |
| `tests/test_module_l5_11_outbox_retry_cap.py` | passes, unchanged |
| `tests/test_module_l5_11_admin_notif_settings.py` | passes, unchanged |
| `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` | passes, `protected==200` unchanged |
| `tests/test_phase2f17a_global_mutation_inventory.py` | passes, `protected==200` unchanged |
| `tests/test_media_engine.py` + `tests/test_p0_enterprise_media_library.py` | 159 combined, 0 failed — confirms the `MediaAssetService`/`asset_service.py` changes (upload, replace_asset, `_assert_chat_thread_authority`) introduced no regression in the general media engine |
| Combined platform_notifications + media-engine run (356 tests) | 356 passed, 0 failed |
| Full repository sweep (`-k "not Live"`) | see `regression-report.md` |

## Updated pre-existing tests (expected consequences of this slice's stricter checks)
- Every test in `test_phase2f18a/b/c_*.py` that mocked the `MediaAsset`
  lookup via `db.get(...)` was updated to mock it via `db.execute(...)`
  returning a `.scalar_one_or_none()` result instead — a direct,
  mechanical consequence of replacing `db.get()` with
  `select(...).with_for_update()` for the atomicity fix. Every updated
  test still asserts the SAME expected outcome (allow/deny) it did before.
- `test_phase2f18b_platform_notifications_media_authority.py::TestMediaAccessServiceReuse::test_technician_can_view_same_tenant_customer_context_asset`
  was RENAMED to
  `test_technician_attaching_unowned_unclaimed_asset_now_rejected` and its
  assertion inverted (was: accepted; now: rejected) — this is a
  deliberate, documented behavior change (this slice's core fix), not a
  weakening. The docstring explains the correction explicitly.
- `test_phase2f18c_platform_notifications_media_sharing_retrieval.py::TestRetrievalTimeThreadAuthority::test_unclaimed_asset_skips_thread_check`
  was renamed to
  `test_unclaimed_asset_skips_thread_check_for_office_persona` and its
  actor changed from `technician` to `staff`, to keep testing the
  UNCHANGED office-persona behavior while the technician case moved to
  this slice's own dedicated, more thorough test coverage.

No test was skipped or deleted. No test's positive-case coverage was
removed — where a test's expected outcome changed, it changed because the
underlying security behavior deliberately changed, and the new expected
outcome is explicitly asserted and documented.
