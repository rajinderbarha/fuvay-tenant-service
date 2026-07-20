# No Partial Persistence / No Delivery Proof (this slice's new paths)

| Rejected scenario | Where validation fires | db.add called? | db.commit called? | Test |
|---|---|---|---|---|
| Unassigned technician access | `validate_thread_access` (via `get_thread`/`list_messages`/`send_message`/`mark_thread_read`) | No | No | `test_unassigned_technician_denied` |
| Technician assigned to a different Job | same | No | No | `test_technician_assigned_to_other_job_denied` |
| Removed participant technician | same | No | No | `test_removed_participant_technician_denied` |
| Technician tenant-membership-only (no assignment/participant) | same | No | No | `test_technician_tenant_membership_alone_is_not_sufficient` |
| Nonexistent media asset referenced | `_validate_attachments`, called from `send_message` before `ChatMessage(...)` construction | No | No | `test_nonexistent_media_asset_rejected` |
| Cross-tenant media asset referenced | same | No | No | `test_cross_tenant_media_asset_rejected` |
| Malformed media_id (not a UUID) | same | No | No | `test_malformed_media_id_rejected` |
| Foreign/missing thread (privacy-equivalent path) | `validate_thread_access` / `get_thread`'s initial existence check | No | No | `test_foreign_tenant_and_missing_thread_share_error_code` |

All 7 new rejected-path tests assert `db.add.assert_not_called()` (and,
where the flow would otherwise reach `db.commit()`, that too is unreached
— proven by the exception propagating out of `send_message`/
`validate_thread_access` before the `await db.commit()` line is ever
executed).

## Delivery side effect
Since `_notify_other_participants` (the only delivery-adjacent call on this
router, writing `InAppNotification` rows) executes AFTER attachment
validation in `send_message`, every rejected-attachment test case above
also proves zero delivery-side-effect rows are created — no separate test
was needed since `db.add.assert_not_called()` covers both the `ChatMessage`
row and any `InAppNotification` row `_notify_other_participants` would
have created.

## Pre-existing rejected paths (unchanged, re-confirmed by 2F-18, not re-tested here)
See `docs/workflow-rearchitecture/phase-02a-slice-02f18/no-partial-persistence-delivery-proof.md`
for the full 2F-18 table (nonexistent/cross-tenant thread records, invalid
visibility, unknown preference event_key/channel) — all still verified
passing by this slice's full regression run.
