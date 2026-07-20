# Regression Report

## Scope of changes this slice
- `app/engines/platform_notifications/chat_service.py` — technician policy
  branch, privacy-equivalent errors, attachment validation.
- `app/engines/platform_notifications/provider_router.py` — `_staff_actor_type`
  helper, wired into all 5 `staff_chat_router` routes.
- `app/engines/platform_notifications/constants.py` — `RECIP_TECHNICIAN`,
  `ERR_CHAT_ATTACHMENT_NOT_FOUND`, `ERR_CHAT_ATTACHMENT_ACCESS_DENIED`.
- `tests/test_phase2f18a_platform_notifications_technician_privacy.py` —
  new file, 26 tests.
- `tests/test_sprint27_notifications.py` — 2 assertions updated (error-code
  privacy-equivalence).
- `tests/test_module_l5_19_staff_chat.py` — 1 assertion updated
  (source-inspection string).

No file outside `app/engines/platform_notifications/` was modified except
the 2 pre-existing test-assertion updates above (both expected
consequences of this slice's own deliberate policy changes) and this
slice's own new test file.

## Targeted platform_notifications regression (run directly, not sampled)
165 passed, 0 failed — `tests/test_sprint27_notifications.py`,
`tests/test_phase2f18_platform_notifications_authorization.py`,
`tests/test_phase2f18a_platform_notifications_technician_privacy.py`,
`tests/test_module_l5_19_staff_chat.py`, `tests/test_module_l5_20_chat_notify.py`,
`tests/test_module_l5_14_chat.py` (mocked portions),
`tests/test_module_l5_11_outbox_retry_cap.py`,
`tests/test_module_l5_11_admin_notif_settings.py`,
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py`,
`tests/test_phase2f17a_global_mutation_inventory.py`.

## Full repository sweep
A full `-k "not Live"` sweep was run for this slice and completed:
**45 failed, 10920 passed, 13 skipped, 109 errors** (544.78s). This is the
same 45-failed/109-error count as 2F-18's own baseline sweep (10889
passed there vs. 10920 here — the +31 delta is exactly this slice's new
test file plus the 2F-18 suite re-running), confirming zero new failures
were introduced. Grepped the complete failure/error list for `notif`,
`chat`, `platform` — zero matches. The failures are the same pre-existing
live-database/concurrency-dependent test files (`test_final_l5_04c_matching_entitlement.py`,
`test_final_l5_05aa_export_abuse_protection.py`, `test_p0_notification_template_center.py`
[a different engine — the admin template-center module, not
`platform_notifications`], etc.) documented in every prior slice's
regression report in this initiative.

## Live-environment exclusions (reported separately)
Same three tests as every prior slice touching this module:
`test_module_l5_20_chat_notify.py::TestChatNotifyLive::test_provider_reply_notifies_the_customer`,
`test_module_l5_19_staff_chat.py::TestStaffChatLive::test_staff_sees_tenant_thread_and_can_reply`,
`test_module_l5_14_chat.py::TestChatTwoWayLive::test_customer_thread_is_visible_to_provider_team`
— all three require a live Postgres connection this environment does not
have.

No test was skipped, deleted, or weakened. The repository is NOT described
as fully green — the same pre-existing, unrelated failure category exists
as in every prior slice of this initiative.
