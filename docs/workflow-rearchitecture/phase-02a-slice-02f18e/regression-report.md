# Regression Report

## Scope of changes this slice
- `app/engines/platform_notifications/chat_service.py` —
  `_validate_attachments`: added the office (tenant_owner/staff)
  first-use ambiguity check (uploader-match required for any
  customer-linked destination thread).
- `app/engines/media/asset_service.py` — new
  `_assert_chat_attachment_lifecycle` (deleted/inactive rejection for
  `chat_attachment` context, applied to `get_asset`,
  `get_local_file_for_serve`, `replace_asset`); new
  `_assert_chat_attachment_replace_authority` (distinguishes view from
  replace authority for `chat_attachment` context), wired into
  `replace_asset`.
- `tests/test_phase2f18e_platform_notifications_office_sharing_and_lifecycle.py`
  — new file, 18 tests.

No pre-existing test required modification this slice (all new checks are
additive — see `test-report.md`). No file in `app/engines/media/` was
modified beyond the narrowly-scoped `asset_service.py` corrections.
`app/engines/media/access.py` (`MediaAccessService`) was NOT modified. No
file outside `platform_notifications` and this one media file was
touched.

## Targeted platform_notifications + media regression (run directly)
374 passed, 0 failed — full suite list in `test-report.md`.

## Full repository sweep
A full `-k "not Live"` sweep was run for this slice and completed:
**45 failed, 10970 passed, 13 skipped, 109 errors** (538.49s). This is the
identical 45-failed/109-error count as 2F-18D's own baseline sweep (10952
passed there vs. 10970 here — the +18 delta is exactly this slice's new
test file), confirming zero new failures were introduced. Grepped the
complete failure/error output for `notif`/`chat`/`platform_not`/`media` —
matches found are the SAME pre-existing, unrelated category documented in
every prior slice's regression report:
- `test_p0_notification_template_center.py` (20 matches) — a DIFFERENT
  engine (admin notification-template-center module, not
  `platform_notifications`), DB-fixture dependent.
- `test_final_l5_04c_matching_entitlement.py` (1 match) — live DB
  entitlement test, unrelated engine.
- `test_phase2d_tenant_access_model.py` (1 match) — the same
  pre-existing, stale assertion failure first flagged in Slice 2F-17A's
  regression report.

Zero matches reference `platform_notifications`, `chat_service`,
`notification_service`, `provider_router`, `customer_router`, or the
`app/engines/media/asset_service.py` corrections made this slice.

## Live-environment exclusions (reported separately)
Same three tests as every prior slice touching this module:
`test_module_l5_20_chat_notify.py::TestChatNotifyLive::test_provider_reply_notifies_the_customer`,
`test_module_l5_19_staff_chat.py::TestStaffChatLive::test_staff_sees_tenant_thread_and_can_reply`,
`test_module_l5_14_chat.py::TestChatTwoWayLive::test_customer_thread_is_visible_to_provider_team`
— all three require a live Postgres connection this environment does not
have. Additionally, per Workstream 6's explicit instruction, this slice
reports (rather than fabricates) the absence of a live two-session
concurrent-claim integration test — see `concurrent-claim-proof.md`.

No test was skipped, deleted, or weakened. The repository is NOT
described as fully green — the same pre-existing, unrelated failure
category exists as in every prior slice of this initiative.
