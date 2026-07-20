# Regression Report

## Scope of changes this slice
- `app/engines/platform_notifications/provider_router.py` — router guards only.
- `app/engines/platform_notifications/customer_router.py` — router guard only (alternate-route fix).
- `app/engines/platform_notifications/chat_service.py` — record-ownership + visibility validation.
- `app/engines/platform_notifications/notification_service.py` — preference validation.
- `app/engines/platform_notifications/models.py` — `is_visible_to` fail-closed fix.
- `app/engines/platform_notifications/constants.py` — 2 new error-code constants.
- `tests/test_phase2f18_platform_notifications_authorization.py` — new file.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` — 1 assertion updated.
- `tests/test_phase2f17a_global_mutation_inventory.py` — 1 assertion updated.
- 2 canonical CSVs updated (row-level guard_status only, no schema change).

No file outside `app/engines/platform_notifications/` was modified except
the two test-assertion updates above (both expected consequences of
correctly increasing the protected count) and the CSV coverage updates.

## Full sweep result
`10889+ passed, 45 failed, 13 skipped, 109 errors` (pytest full sweep,
`-k "not Live"`, 3 known live-DB test files excluded exactly as in every
prior slice of this initiative).

## Failures/errors attributable to this slice
**None.** Confirmed by:
1. Grepping the full failure/error list for `notif`, `chat`, `platform` —
   zero matches (the one apparent near-match, `test_p0_notification_template_center.py`,
   is a wholly different engine — the ADMIN notification-template-center
   module, not `platform_notifications`, and its failures are `ERROR`s from
   a missing-DB fixture, not `FAILED` assertions).
2. Running this slice's own suite
   (`tests/test_phase2f18_platform_notifications_authorization.py`) and the
   full pre-existing `platform_notifications` suites in isolation — all
   pass (see `test-report.md`).
3. The failed/error tests are the same category seen in every prior
   slice's regression report in this initiative — concurrency tests, live
   asyncpg-connection tests, and DB-fixture-dependent tests, none of which
   can run without a live Postgres instance in this environment.

## Pre-existing unrelated failures (sample, not exhaustive — same category reported every slice)
- `test_final_l5_04c_matching_entitlement.py` — live DB entitlement tests.
- `test_final_l5_05aa_export_abuse_protection.py` — live concurrency tests.
- `test_final_l5_05k_topup_migration.py` — live concurrency tests.
- `test_final_l5_05s_export_worker_runtime.py` — live DB worker tests.
- `test_p0_notification_template_center.py`, `test_p0_service_options_enterprise.py`,
  `test_p0_sidebar_duplicate_cleanup.py`, `test_trust_quality_phase1.py` —
  all DB-fixture-dependent, unrelated engines.

## Live-environment exclusions (reported separately, per mission requirement)
`test_module_l5_20_chat_notify.py::TestChatNotifyLive::test_provider_reply_notifies_the_customer`,
`test_module_l5_19_staff_chat.py::TestStaffChatLive::test_staff_sees_tenant_thread_and_can_reply`,
`test_module_l5_14_chat.py::TestChatTwoWayLive::test_customer_thread_is_visible_to_provider_team`
— all three require a live Postgres connection (`asyncpg.connect(...)`)
which this environment does not have; same exclusion reported in every
prior slice touching this module.
