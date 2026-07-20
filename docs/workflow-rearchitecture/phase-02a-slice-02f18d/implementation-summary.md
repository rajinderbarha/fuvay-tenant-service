# Slice 2F-18D — Implementation Summary

## Mission
Close the final chat-media authorization boundary: 2F-18C proved
`assert_can_view` is not sufficient for redistribution and built a
thread-claim lock, but never restricted WHO could perform the FIRST claim
(any authorized viewer — including a tenant-wide technician with no
special relationship to the asset — could claim an unclaimed asset into
any thread they could reach), never made the claim write atomic against
concurrent requests, and never audited whether other writers of
`metadata_json` could tamper with an existing claim.

## What was fixed

### 1. Safe first-use destination authority
Previously: any principal that passed `MediaAccessService.assert_can_view`
(which, for `chat_attachment` context, includes ANY same-tenant
`tenant_owner`/`staff`/`technician`) could first-claim an unclaimed asset
into whichever thread they happened to be sending a message in — "first
thread supplied by the caller" was treated as sufficient provenance.
Fixed: for a **technician** specifically, first-use claiming an unclaimed
asset now ALSO requires `asset.uploaded_by_user_id == actor.user_id` — the
only evidence this codebase has that a technician legitimately originated
that asset for a Job. Office personas (`tenant_owner`/`staff`) and
customers were already sufficiently evidenced by the existing
tenant/customer-match + `MediaAccessService` checks (2F-18B/C) and are
unaffected — see `first-use-destination-authority.md` for the full
per-persona classification.

### 2. Atomic claiming
Previously: the asset row was fetched with `db.get()` (no lock), read in
Python, and written back later in the same function — a classic
check-then-act race. Fixed: the asset lookup now uses
`SELECT ... FOR UPDATE` (`select(MediaAsset).where(...).with_for_update()`),
locking the row for the remainder of the current transaction. A concurrent
request targeting the SAME asset blocks until this transaction commits or
rolls back, then re-reads the now-current claim and correctly loses the
race if it targets a different thread. No migration, no new mechanism —
the existing Postgres row lock the async driver already supports.

### 3. Claim metadata tampering resistance
Audited every writer of `MediaAsset.metadata_json` (exactly two:
`upload()` and `replace_asset()` — confirmed by full-file grep, no generic
admin/worker metadata-update route exists at all). Fixed:
- `upload()` now strips a client-supplied `chat_thread_id` key before
  persisting (defensive — the sole caller never passes `extra_metadata`
  today, so this closes a theoretical future-caller injection vector, not
  a live one).
- `replace_asset()` now requires the SAME thread-authority check retrieval
  uses (`_assert_chat_thread_authority`) before allowing a claimed
  `chat_attachment` asset's file content to be swapped — previously a
  same-tenant user authorized to "replace" media in general
  (`assert_can_replace`'s tenant-wide rule) could silently swap a claimed
  asset's content without ever proving they belonged to its conversation.

### 4. Malformed/conflicting claim fail-closed
Previously: `(asset.metadata_json or {}).get("chat_thread_id")` implicitly
trusted `metadata_json` to be a dict and the claim value to be UUID-shaped
— a corrupted or non-dict `metadata_json`, or a non-UUID claim value,
would either crash or (worse) be silently treated as "unclaimed" and
overwritten. Fixed in BOTH `chat_service._validate_attachments` and
`MediaAssetService._assert_chat_thread_authority`: a non-dict
`metadata_json`, or a claim value that doesn't parse as a UUID, now fails
closed with the same privacy-equivalent rejection — never silently
reinterpreted as "no claim exists."

### 5. Unclaimed-asset retrieval policy (symmetric with attach-time)
The same technician-uploader restriction was applied at RETRIEVAL time in
`MediaAssetService._assert_chat_thread_authority`'s unclaimed branch —
previously this method returned immediately for any unclaimed asset
(deferring entirely to `assert_can_view`'s tenant-wide rule); now a
technician additionally needs to be the uploader to VIEW an unclaimed
asset, not just to attach one.

## What was investigated and found not further closable (honestly disclosed)
- **Office (`tenant_owner`/`staff`) unclaimed-asset access remains
  tenant-wide** — this is the SAME ratified, existing, unmodified
  `MediaAccessService` policy reused since 2F-18B; narrowing it further
  would be a much larger change to the general media engine's core
  access model, out of this slice's narrow chat-attachment-only mandate.
- **Permanent/signed-URL revocation after access loss**: confirmed
  unchanged from 2F-18C — `preview_url` for non-public assets already
  defaults to the authenticated API path (re-checked on every call), not
  a raw, unauthenticated storage URL; there is no separate signed-URL
  mechanism in this codebase to audit beyond what 2F-18C already covered.
- **Duplicate-key / multiple-writers race beyond the single claim key**:
  not applicable — `metadata_json` has exactly one server-owned key this
  slice's mechanism cares about (`chat_thread_id`); no other writer path
  exists that could introduce a competing key.

## Coverage
Unchanged at 200/226 — this slice deepened first-use/atomicity/integrity
policy behind the same 10 already router-guarded routes. See
`canonical-coverage-reconciliation.md`.

## Tests
12 new tests
(`tests/test_phase2f18d_platform_notifications_first_use_and_claim_integrity.py`),
all passing. Combined targeted regression: 356 passed, 0 failed. Full
repository sweep: see `regression-report.md`.

## Final status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED** —
see `approval-gate.md`.
