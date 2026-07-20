# Claim Transaction Trace

## Exact sequence within `ChatMessageService.send_message`
1. **Asset SELECT FOR UPDATE** — `select(MediaAsset).where(MediaAsset.id ==
   asset_id).with_for_update()`, executed via `db.execute(...)`, on the
   SAME `db: AsyncSession` object passed into `send_message` from the
   router.
2. **Existing claim read** — `asset.metadata_json.get("chat_thread_id")`,
   read from the now-locked in-memory row (2F-18D).
3. **Thread and recipient validation** — actually runs BEFORE step 1 in
   real order (`validate_thread_access` is called earlier in
   `send_message`, before the attachment loop even starts) — re-confirmed
   this slice, unchanged.
4. **Media validation** — lifecycle/context/tenant/customer/
   `MediaAccessService`/first-use/office-ambiguity (this slice) checks,
   all within the SAME loop iteration as step 1-2, same session.
5. **Claim assignment** — `asset.metadata_json = new_meta`, a plain
   Python attribute set on the SQLAlchemy-mapped object — no explicit
   `db.execute`/`db.flush` call for this specific write; SQLAlchemy's
   unit-of-work tracks the change and will include it in the next flush.
6. **Message creation** — `msg = ChatMessage(...)`; `db.add(msg)`.
7. **Flush** — no EXPLICIT flush call exists in `send_message` at all;
   the first point data actually reaches the database is `db.commit()`
   (which implicitly flushes pending changes as part of the commit
   sequence) — confirmed by direct code read, unchanged this slice.
8. **Commit** — `await db.commit()`, the ONLY commit call in the entire
   method.
9. **Delivery/event enqueue** — `_notify_other_participants` (writes
   `InAppNotification` rows via `db.add`) runs BEFORE `db.commit()`
   (immediately preceding it in the method body) — so notification rows
   are part of the SAME transaction/commit as the claim and the message.

## Session identity
One single `db: AsyncSession` instance flows through the entire call —
passed by the router, threaded through `send_message` → `_validate_attachments`
→ `_notify_other_participants`, never swapped or re-acquired. No nested
transaction, no intermediate `db.commit()`, confirmed by:
- Direct code read (only one `await db.commit()` call exists in
  `send_message`).
- `test_no_commit_before_claim_and_message_are_both_ready` — directly
  instruments `db.add` to record `db.commit.call_count` at the moment
  each object (message, notifications) is added, asserting it is always
  `0` — i.e., NOTHING is committed before every piece of state for this
  operation is ready.

## Lock release point
The `FOR UPDATE` lock (2F-18D) is a database-level construct tied to the
transaction, not to any Python-level object — it is released only when
the underlying transaction ends (commit or rollback), which in this
codebase's session-management pattern happens at `db.commit()` (success)
or when an exception propagates out of the request handler and the
session is closed/rolled back by the surrounding framework (failure) —
the SAME mechanism every prior slice's "no partial persistence" proofs
have relied on.

## The asset claim and the message use the same transaction and session
Confirmed directly — both are Python-level mutations tracked by the SAME
`AsyncSession` object (`db`), flushed together, committed together by the
single `await db.commit()` call. There is no code path where one could be
persisted without the other.
