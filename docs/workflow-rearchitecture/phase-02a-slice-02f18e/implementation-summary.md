# Slice 2F-18E — Implementation Summary

## Mission
Close the final remaining chat-media controls 2F-18D left open: office
(tenant_owner/staff) could still first-claim ANY unclaimed, tenant/customer-
matched asset into ANY customer-linked thread with no proof of WHICH of the
customer's (possibly several) Jobs/conversations it belonged to;
`replace_asset` still let anyone with generic media VIEW authority
overwrite another user's asset content; the transaction/atomicity
guarantees built in 2F-18D were never explicitly traced or proven with a
dedicated test; and retrieval never rejected soft-deleted or
non-`active`-status `chat_attachment` assets.

## What was fixed

### 1. Office first-use ambiguity closed
Previously: `tenant_owner`/`staff` could first-claim any unclaimed,
tenant+customer-matched asset into any thread belonging to that customer
— even though the SAME customer can have multiple concurrent
Jobs/threads, and `MediaAsset` has no Job/thread column to disambiguate
which one the asset was actually "for." Fixed: for a thread WITH a
customer party (`thread.customer_id is not None` — i.e. any Job-linked or
customer-facing conversation), an office actor may now only first-claim
an asset they themselves uploaded — mirroring the technician rule from
2F-18D. A thread with NO customer party (a provider-internal
conversation) carries no external-audience risk and is unaffected —
office may freely first-claim tenant-matched assets there, matching the
ratified policy's explicit "provider-internal asset shared only into a
provider-internal thread by an authorized owner/staff actor" allowance.

### 2. `replace_asset` — view authority is no longer replace authority
Previously: `assert_can_replace` reused `assert_can_delete`'s
tenant-wide-for-media rule — any same-tenant `tenant_owner`/`staff`/
`technician` who could VIEW a customer-context asset could also REPLACE
its file content. Fixed, scoped to `chat_attachment` context: a new
`_assert_chat_attachment_replace_authority` requires either (a) the actor
is the asset's own uploader, or (b) the actor is `tenant_owner`/`staff`
AND passes the SAME `require_owner_or_office_staff_mutation` mutation-
scope check reused throughout this series (denies read-only access_scope)
AND the asset belongs to their tenant. A customer or technician who can
merely view a same-tenant asset can no longer replace someone else's
upload.

### 3. Retrieval lifecycle enforcement
Previously: `_load`'s filter only excluded the literal `status ==
"deleted"` string — a `chat_attachment` asset with `deleted_at` set (soft
delete) or any OTHER non-`"active"` status (e.g. `"quarantined"`) was
still retrievable via `get_asset`/`get_local_file_for_serve`/
`replace_asset`, even though the SAME asset was already correctly
rejected at ATTACH time (2F-18B). Fixed: a new
`_assert_chat_attachment_lifecycle` check, scoped to `chat_attachment`
context, rejects any asset with `deleted_at` set or `status != "active"`
at every retrieval and replacement entry point — raising the SAME
`NotFoundException` a missing asset would (privacy equivalent).

### 4. Transaction/atomicity proof
No code change was needed here (2F-18D's design already had the correct
properties) — this slice adds the PROOF that was previously only
asserted, not tested: `test_no_commit_before_claim_and_message_are_both_ready`
directly verifies `db.commit()` is never called before the claim and
message are both ready to persist, and `test_commit_failure_propagates_not_swallowed`
proves a downstream failure is never silently caught (the precondition for
the standard session-rollback mechanism this codebase relies on
throughout to actually undo an in-memory claim write).

## What was investigated and found already correct / out of proportion to change
- **Delivery ordering**: re-traced, unchanged from 2F-18/2F-18C —
  `_notify_other_participants` still runs strictly after all validation
  and claim-assignment, strictly before `db.commit()`, and this module
  remains `DATABASE_ONLY_NOTIFICATION_RECORD` (no external queue/dispatch
  exists at all to reorder).
- **Live two-session concurrency test**: not built — this environment has
  no live Postgres instance (confirmed unavailable throughout this entire
  five-plus-slice series). Per the mission's own fallback instruction,
  this is reported as a live-environment exclusion, not silently skipped
  or falsely claimed as executed — see `concurrent-claim-proof.md`.
- **Recipient compatibility beyond the office first-use fix**: re-examined
  against 2F-18C's own reasoning (`attachment-recipient-authority.md`) —
  no new gap was found beyond the office first-use ambiguity itself; every
  recipient who can read a thread has already passed the identical
  authority the sender needed, and retrieval-time re-validation (2F-18C)
  remains the enforcement point for individual recipients.

## Coverage
Unchanged at 200/226 — this slice deepened first-use/replacement/lifecycle
policy behind the same 10 already router-guarded routes. See
`canonical-coverage-reconciliation.md`.

## Tests
18 new tests
(`tests/test_phase2f18e_platform_notifications_office_sharing_and_lifecycle.py`),
all passing. Combined targeted regression: 374 passed, 0 failed. Full
repository sweep: see `regression-report.md`.

## Final status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED** —
see `approval-gate.md`.
