# Delivery Ordering

## Unchanged finding from 2F-18, re-verified with the new checks inserted at the correct point
`send_message`'s validation order is now:

1. Authenticate (`get_current_user`, FastAPI dependency layer).
2. Authorize persona/scope (`require_owner_or_office_staff_mutation` /
   `require_staff_or_technician_only` / `require_customer`, dependency layer).
3. Validate thread exists (`ERR_CHAT_THREAD_NOT_FOUND`).
4. Validate thread not terminal (`ERR_CHAT_THREAD_CLOSED`).
5. Validate tenant/participant/assignment authority
   (`validate_thread_access` — includes this slice's technician
   assignment/participant check).
6. Validate `can_send` participant flag (`ERR_CHAT_CANNOT_SEND`).
7. Validate message has content (`ERR_CHAT_MESSAGE_REQUIRED`).
8. Validate visibility enum + non-admin restriction (`ERR_CHAT_INVALID_VISIBILITY`).
9. **Validate attachments (`ERR_CHAT_ATTACHMENT_NOT_FOUND`) — NEW this
   slice, inserted here, still strictly before persistence.**
10. Construct `ChatMessage`, `db.add`.
11. Update `thread.last_message_at`.
12. `_notify_other_participants` (writes `InAppNotification` rows — the
    only delivery side effect on this router).
13. `db.commit()`.

Every validation step (3-9) raises BEFORE step 10 — a rejection at any
point produces zero `db.add` calls and zero commit, proven directly by
`no-partial-persistence-delivery-proof.md`'s new attachment-specific test
cases (`test_nonexistent_media_asset_rejected`,
`test_cross_tenant_media_asset_rejected`,
`test_malformed_media_id_rejected` all assert
`db.add.assert_not_called()`).

## No external delivery exists on this router (unchanged from 2F-18)
`DATABASE_ONLY_NOTIFICATION_RECORD` — `_notify_other_participants` writes
only `InAppNotification` rows, synchronously, in the same transaction as
the message. No queue, no worker, no external provider call exists on any
path reachable from `provider_router.py`, `staff_notif_router`,
`staff_chat_router`, or `customer_router.py`. Re-confirmed by code read
this slice (no new delivery mechanism was introduced).
