# Regression Report

## Scope of changes this slice
- `app/engines/platform_notifications/chat_service.py` — `_validate_attachments`:
  asset lookup changed from `db.get()` to `SELECT ... FOR UPDATE`
  (atomicity); added technician first-use uploader-match check; hardened
  claim parsing to fail closed on non-dict `metadata_json` or non-UUID
  claim values.
- `app/engines/media/asset_service.py` — `_assert_chat_thread_authority`:
  added the unclaimed-technician uploader-match restriction; hardened
  claim parsing identically. `upload()`: strips a client-supplied
  `chat_thread_id` via new `_strip_claim_key` helper. `replace_asset()`:
  now requires `_assert_chat_thread_authority` for claimed
  `chat_attachment` assets before allowing file replacement.
- `tests/test_phase2f18d_platform_notifications_first_use_and_claim_integrity.py`
  — new file, 12 tests.
- `tests/test_phase2f18a/b/c_*.py` — mock updates (asset lookup mocking
  changed from `db.get` to `db.execute`), 1 test rewritten (2F-18B) to
  reflect the corrected technician policy, 1 test renamed (2F-18C) to
  keep testing the unchanged office-persona case.

No file in `app/engines/media/` was modified beyond the narrowly-scoped
`asset_service.py` corrections (permitted explicitly by this slice's
mission as being within "the direct chat_attachment authorization,
metadata, or retrieval chain"). `app/engines/media/access.py`
(`MediaAccessService`) was NOT modified. No file outside
`platform_notifications` and this one media file was touched, except the
pre-existing test-fixture updates.

## Targeted platform_notifications + media regression (run directly)
356 passed, 0 failed — full suite list in `test-report.md`.

## Full repository sweep
A full `-k "not Live"` sweep was run for this slice and completed:
**45 failed, 10952 passed, 13 skipped, 109 errors** (523.33s). This is the
identical 45-failed/109-error count as 2F-18C's own baseline sweep (10940
passed there vs. 10952 here — the +12 delta is exactly this slice's new
test file), confirming zero new failures were introduced. Grepped the
complete failure/error output for `notif`/`chat`/`platform_not`/`media` —
22 matches, ALL in the same pre-existing, unrelated category documented in
every prior slice's regression report:
- `test_p0_notification_template_center.py` (20 matches) — a DIFFERENT
  engine (the admin notification-template-center module, not
  `platform_notifications`), DB-fixture dependent.
- `test_final_l5_04c_matching_entitlement.py` (1 match) — live DB
  entitlement test, unrelated engine.
- `test_phase2d_tenant_access_model.py` (1 match) — the same
  pre-existing, stale assertion failure first flagged in Slice 2F-17A's
  regression report (unrelated to any change in this session).

Zero matches reference `platform_notifications`, `chat_service`,
`notification_service`, `provider_router`, `customer_router`, or the
`app/engines/media/asset_service.py` corrections made this slice.

## Live-environment exclusions (reported separately)
Same three tests as every prior slice touching this module:
`test_module_l5_20_chat_notify.py::TestChatNotifyLive::test_provider_reply_notifies_the_customer`,
`test_module_l5_19_staff_chat.py::TestStaffChatLive::test_staff_sees_tenant_thread_and_can_reply`,
`test_module_l5_14_chat.py::TestChatTwoWayLive::test_customer_thread_is_visible_to_provider_team`
— all three require a live Postgres connection this environment does not
have. Additionally, this slice's atomicity claim (`SELECT ... FOR UPDATE`
correctly serializing two REAL concurrent transactions) could not be
verified against a live database either — see `known-limitations.md`
item 9.

No test was skipped, deleted, or weakened. The repository is NOT
described as fully green — the same pre-existing, unrelated failure
category exists as in every prior slice of this initiative.
