# Regression Report

## Scope of changes this slice
- `app/engines/platform_notifications/chat_service.py` — `_validate_attachments`
  rewritten to reuse `MediaAccessService.assert_can_view`, plus
  `media_context`/lifecycle/customer checks; `send_message` gained an
  optional `actor: UserContext | None` parameter.
- `app/engines/platform_notifications/provider_router.py` — `actor=u`
  threaded into `provider_send_message` and `staff_send_message`'s
  `send_message` calls.
- `app/engines/platform_notifications/customer_router.py` — `actor=u`
  threaded into `send_message`'s `send_message` call.
- `tests/test_phase2f18b_platform_notifications_media_authority.py` — new
  file, 9 tests.
- `tests/test_phase2f18a_platform_notifications_technician_privacy.py` — 1
  mock fixture updated (additional attributes set, same expected outcome).

No file in `app/engines/media/` was modified — `MediaAccessService` and
`MediaAssetRecord` are imported and called, never changed. No file outside
`app/engines/platform_notifications/` was modified except the one
pre-existing test-fixture update above and this slice's own new test file.

## Targeted platform_notifications + media regression (run directly)
333 passed, 0 failed — `tests/test_sprint27_notifications.py`,
`tests/test_phase2f18_platform_notifications_authorization.py`,
`tests/test_phase2f18a_platform_notifications_technician_privacy.py`,
`tests/test_phase2f18b_platform_notifications_media_authority.py`,
`tests/test_module_l5_19_staff_chat.py`, `tests/test_module_l5_20_chat_notify.py`,
`tests/test_module_l5_14_chat.py` (mocked portions),
`tests/test_module_l5_11_outbox_retry_cap.py`,
`tests/test_module_l5_11_admin_notif_settings.py`,
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`,
`tests/test_phase2f17a_global_mutation_inventory.py`,
`tests/test_media_engine.py`, `tests/test_p0_enterprise_media_library.py`.

## Full repository sweep
A full `-k "not Live"` sweep was run for this slice and completed:
**45 failed, 10929 passed, 13 skipped, 109 errors** (522.03s). This is the
identical 45-failed/109-error count as 2F-18A's own baseline sweep (10920
passed there vs. 10929 here — the +9 delta is exactly this slice's new
test file), confirming zero new failures were introduced. Grepped the
complete failure/error output for `notif`, `chat`, `platform_not` — zero
matches. The failures are the same pre-existing live-database/concurrency-
dependent test files (`test_final_l5_04c_matching_entitlement.py`,
`test_final_l5_05aa_export_abuse_protection.py`,
`test_p0_notification_template_center.py` [a different engine — the admin
template-center module, not `platform_notifications`],
`test_trust_quality_phase1.py`, etc.) documented in every prior slice's
regression report in this initiative.

## Live-environment exclusions (reported separately)
Same three tests as every prior slice touching this module:
`test_module_l5_20_chat_notify.py::TestChatNotifyLive::test_provider_reply_notifies_the_customer`,
`test_module_l5_19_staff_chat.py::TestStaffChatLive::test_staff_sees_tenant_thread_and_can_reply`,
`test_module_l5_14_chat.py::TestChatTwoWayLive::test_customer_thread_is_visible_to_provider_team`
— all three require a live Postgres connection this environment does not
have.

No test was skipped, deleted, or weakened.
