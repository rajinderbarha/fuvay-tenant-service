# Atomic Claiming

## Mechanism: `SELECT ... FOR UPDATE`
`chat_service._validate_attachments` previously fetched each referenced
`MediaAsset` via `db.get(MediaAsset, asset_id)` — a plain, non-locking
read. Fixed this slice:

```python
r = await db.execute(
    select(MediaAsset).where(MediaAsset.id == asset_id).with_for_update()
)
asset = r.scalar_one_or_none()
```

`with_for_update()` issues a Postgres row-level `FOR UPDATE` lock, held
for the remainder of the CURRENT transaction (`send_message` does not
commit until after message persistence + `_notify_other_participants`, so
the lock spans the entire attach-and-persist operation). Verified directly
by compiling the constructed query and asserting `"FOR UPDATE"` appears in
the compiled SQL (`test_asset_lookup_uses_select_for_update`) — not merely
asserted from reading the code.

## Transaction sequence (traced, per Workstream 7)
1. Asset lookup — NOW locks the row (`SELECT ... FOR UPDATE`).
2. Claim read — from the now-locked row's in-memory `metadata_json`.
3. Thread validation — `validate_thread_access` (runs BEFORE the asset
   loop even starts, unchanged from 2F-18A).
4. Media validation — lifecycle/context/tenant/customer/`MediaAccessService`/
   first-use checks (this slice adds the malformed-claim and
   technician-uploader checks to this step).
5. Claim assignment — the two-pass design (validate ALL referenced assets
   first, THEN claim ALL of them) means no asset is claimed until every
   asset in the message has passed every check — a later asset's failure
   leaves an EARLIER asset's lock released via transaction rollback with
   no claim ever written (proven since 2F-18C,
   `test_partial_batch_failure_does_not_claim_earlier_asset`, re-passing
   this slice with the FOR UPDATE change).
6. Message persistence — `db.add(msg)`.
7. Commit — `await db.commit()`, releasing all locks held by this
   transaction.
8. Delivery enqueue — `_notify_other_participants` (runs before commit,
   still within the same locked transaction).

## Concurrency guarantees
- **Same asset, same thread (two concurrent requests)**: both requests
  lock sequentially (Postgres serializes `FOR UPDATE` acquisition on the
  same row); the first to commit sets the claim; the second, on acquiring
  the now-released lock, re-reads the (now-set, matching) claim and
  succeeds idempotently (per the established same-thread-reuse policy).
- **Same asset, different threads (two concurrent requests)**: the first
  transaction to acquire the lock claims the asset for its thread and
  commits; the second, blocked until the first releases the lock, re-reads
  the claim, finds it set to a DIFFERENT thread, and is rejected via the
  standard `claimed_thread_id != thread.id` check — **at most one
  different-thread claim succeeds**, by construction of the lock plus the
  existing conflict check (no new conflict-detection code was needed
  beyond what 2F-18C already had; the lock is what makes the EXISTING
  check race-free).
- **Authorized request versus unauthorized request**: unaffected by
  locking — an unauthorized request never reaches the claim-application
  pass regardless of timing, since authorization checks (thread access,
  `MediaAccessService`, first-use) all run before the lock is even
  meaningfully consulted for conflict purposes.
- **Failure after claim but before message persistence**: cannot occur
  under the current design — claims are applied ONLY after ALL validation
  for ALL assets has succeeded, immediately before message construction;
  there is no window where a claim is set but the message might still
  fail validation afterward.
- **Transaction rollback after provisional claim**: if `db.commit()`
  itself fails (e.g., a downstream constraint violation not modeled in
  this slice's scope) after the claim was set in-memory and flushed, the
  standard SQLAlchemy/Postgres rollback-on-exception behavior (relied upon
  by every prior slice's "no partial persistence" proofs) restores the
  prior `metadata_json` value — this is existing session-lifecycle
  behavior, not something this slice introduces or could test with mocks
  (no real DB transaction exists in the mocked unit-test environment).

## Why not a migration-based mechanism
The mission explicitly forbids adding a migration solely for claim
atomicity. `with_for_update()` requires zero schema changes — it operates
entirely on the EXISTING primary-key-indexed `id` column, which already
has an implicit unique index (primary key) that Postgres uses to acquire
the row lock efficiently.
