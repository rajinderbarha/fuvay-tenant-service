# No Partial State Proof (this slice's new paths)

| Rejected scenario | Where validation fires | db.add called? | db.commit called? | Claim written? | Test |
|---|---|---|---|---|---|
| Office (staff) first-use claim of an unowned asset into a customer-linked thread | `_validate_attachments`, before the claim-application pass | No | No | No — `unowned.metadata_json.get("chat_thread_id")` asserted still `None` | `test_staff_cannot_first_claim_unowned_asset_into_customer_thread`, `test_ambiguous_office_share_persists_nothing` |
| Office (tenant_owner) — same rule | same | No | No | No | `test_tenant_owner_same_ambiguity_rule_as_staff` |
| Commit failure (simulated) | `send_message`'s final `await db.commit()` | Yes (message/notification objects WERE added to the session, but never persisted since commit never succeeds) | Raises (propagates) | Claim was set in-memory but never committed — relies on the caller's session rollback to undo it, consistent with every prior slice | `test_commit_failure_propagates_not_swallowed` |
| `replace_asset` denial (readonly staff / non-uploader customer / non-uploader technician / foreign tenant) | `_assert_chat_attachment_replace_authority`, before file storage or any DB write | n/a (raises before `MediaAsset(...)` construction) | n/a | No — old asset's claim/status untouched | `test_readonly_staff_denied_replace`, `test_customer_cannot_replace_provider_asset`, `test_technician_cannot_replace_unowned_asset`, `test_foreign_tenant_staff_denied_replace` |
| `replace_asset` on a deleted/inactive `chat_attachment` asset | `_assert_chat_attachment_lifecycle`, before authorization is even checked | n/a | n/a | No | `test_deleted_chat_attachment_rejected`, `test_quarantined_chat_attachment_rejected` (via the shared helper method, applicable to `replace_asset`'s call site) |

All rejected-attachment tests assert `db.add.assert_not_called()` where
applicable. The one intentionally-different case (`test_commit_failure_propagates_not_swallowed`)
documents that `db.add` DOES get called (the message/notification are
added to the session in the normal flow) but the exception at `commit()`
means nothing is ever actually persisted — this is the expected,
documented behavior for a mid-transaction failure, not a violation of the
no-partial-persistence principle (since nothing reaches the database
without a successful commit).

## Pre-existing rejected paths (unchanged, re-confirmed by 2F-18 through 2F-18D, not re-tested here)
All prior slices' `no-partial-persistence*.md`/`no-partial-state*.md`
proofs re-confirmed still passing by this slice's full regression run
(374 targeted tests, 0 failures).
