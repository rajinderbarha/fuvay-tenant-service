# Test Report

| Suite | Result |
|---|---|
| `tests/test_phase2f18a_platform_notifications_technician_privacy.py` (new) | 26 passed |
| `tests/test_phase2f18_platform_notifications_authorization.py` (2F-18, unchanged) | 49 passed |
| `tests/test_sprint27_notifications.py` (pre-existing, 2 assertions updated) | all mocked tests pass |
| `tests/test_module_l5_19_staff_chat.py` (1 assertion updated) | mocked portion passes; `*Live*` excluded (no DB) |
| `tests/test_module_l5_20_chat_notify.py` | mocked portion passes; `*Live*` excluded (no DB) |
| `tests/test_module_l5_14_chat.py` | mocked portion passes; `*Live*` excluded (no DB) |
| `tests/test_module_l5_11_outbox_retry_cap.py` | passes, unchanged |
| `tests/test_module_l5_11_admin_notif_settings.py` | passes, unchanged |
| `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` | passes, `protected==200` assertion unchanged from 2F-18 |
| `tests/test_phase2f17a_global_mutation_inventory.py` | passes, `protected==200` assertion unchanged from 2F-18 |
| Combined platform_notifications-focused run (165 tests) | 165 passed, 0 failed |
| Full repository sweep (`-k "not Live"`) | in progress at time of writing; see `regression-report.md` for final tally — same pre-existing live-DB-dependent failure category observed in every prior slice, none referencing `platform_notifications`/`chat_service`/`notification_service`/`provider_router`/`customer_router` |

## Updated pre-existing tests (both expected consequences of deliberate policy changes)
- `test_sprint27_notifications.py::test_chat_thread_customer_cannot_access_other_customer`
  and `::test_chat_thread_provider_cannot_access_other_tenant`: error-code
  assertion changed `ERR_CHAT_THREAD_ACCESS_DENIED` → `ERR_CHAT_THREAD_NOT_FOUND`
  (privacy-equivalence fix, this slice).
- `test_module_l5_19_staff_chat.py::TestStaffChatSource::test_staff_chat_router_exists_and_is_tenant_scoped`:
  source-inspection assertion changed `"RECIP_STAFF" in src` →
  `"_staff_actor_type(u)" in src` (technician/staff persona split, this
  slice).

No test was skipped, deleted, or weakened. Both updates are documented,
deliberate consequences of a security-hardening change, not adjustments to
make a bug pass.
