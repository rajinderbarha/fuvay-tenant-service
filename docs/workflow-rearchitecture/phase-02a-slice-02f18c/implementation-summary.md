# Slice 2F-18C — Implementation Summary

## Mission
Close the residual media-SHARING and media-RETRIEVAL gaps 2F-18B left
open: `MediaAccessService.assert_can_view` proves the SENDER may view an
asset, but 2F-18B never distinguished "may view" from "may redistribute
into a conversation," never verified every intended RECIPIENT could
receive it, never prevented a same-customer asset being reused across
different Jobs/conversations, and never applied any thread-equivalent
authority at the actual RETRIEVAL routes (`GET /v1/media/{id}/view`,
`/download`) — a technician denied from a thread could still fetch its
media directly if they separately had generic tenant-role media view
rights.

## What was fixed

### 1. Thread-claim lock — closes same-customer cross-Job/cross-conversation reuse
`MediaAsset` has no `job_id`/`thread_id` column (no migration permitted).
Fixed using ONLY the asset's EXISTING `metadata_json` JSONB column: the
FIRST thread a `chat_attachment` asset is successfully attached to claims
it (`metadata_json["chat_thread_id"] = str(thread.id)`, written only after
every other check for every asset in the message has passed — no partial
claim on a multi-attachment message that fails partway through). Any LATER
attempt to attach the SAME asset to a DIFFERENT thread is rejected with
the same privacy-equivalent error code. This directly closes: "ServiceJob
A1's photo reused in ServiceJob A2's thread" — same customer, same tenant,
previously indistinguishable, now rejected
(`test_cross_job_reuse_within_same_customer_rejected`).

### 2. Retrieval-time thread authority — closes the direct-download bypass
Added `MediaAssetService._assert_chat_thread_authority` (in
`app/engines/media/asset_service.py` — the smallest safe correction, as
explicitly permitted by this slice's mission, since the fix is directly
required by chat-attachment retrieval). For any `chat_attachment`-context
asset that HAS been claimed by a thread, `get_asset`/`get_local_file_for_serve`
(reached by `GET /v1/media/{id}`, `/view`, `/download`) now ALSO require
the requesting principal to pass `ChatThreadService.validate_thread_access`
for that exact thread — reusing `platform_notifications`' own,
already-hardened (2F-18A) thread-authority rule. This means:
- An unassigned technician can no longer retrieve a Job-thread's media
  directly, even with generic tenant-role media-view rights
  (`test_unassigned_technician_denied_retrieval_of_job_thread_media`).
- A technician assigned to a DIFFERENT Job is denied the same way.
- `super_admin` still bypasses (matches every other authority layer in
  this codebase).
- An asset never yet claimed by any thread (not yet shared into a
  conversation) is unaffected — falls back to `MediaAccessService`'s own
  tenant/customer rule only.

### 3. Retrieval-path privacy equivalence for chat attachments
Fixed: for `chat_attachment`-context assets specifically, BOTH the
"missing" case and any authorization denial (from `MediaAccessService` OR
the new thread-authority check) now raise the SAME `NotFoundException` —
closing the retrieval-path privacy gap 2F-18B identified but left
unfixed as "out of scope" (this slice's mission explicitly asked for the
correction to be "applied to the actual retrieval route, not only
attachment validation"). Scoped narrowly to `chat_attachment` context only
— every other media context's error behavior is completely unchanged.

### 4. Dropped `media_ids` resolved (SAFE_SUPPORT)
`staff_send_message` previously accepted `media_ids` on its schema but
never forwarded them to the service layer — silently discarded, not
insecure but non-functional. Fixed: now forwarded through the exact same
validated path `provider_send_message` uses (SAFE_SUPPORT disposition per
the mission's own menu, chosen because the validation infrastructure
already existed and required no new code to wire up safely).

## What was investigated and found not fully closable (honestly disclosed)
- **Recipient authorization for every thread participant at send time**:
  NOT independently re-verified per-recipient at send time. Reasoned
  through, not built, because every participant who can read a message at
  all has ALREADY passed the identical `validate_thread_access` gate the
  sender passed (technician assignment/participant policy, customer
  ownership, tenant match) — building a redundant per-recipient
  `MediaAccessService.assert_can_view` loop at send time would not close
  any gap the thread-read gate doesn't already close, since reading the
  message IS reading the attachment reference. See
  `attachment-recipient-authority.md` for the full reasoning.
- **Participant-removal media revocation**: partially closed as a SIDE
  EFFECT of fix #2 — a removed participant fails `validate_thread_access`
  (2F-18A's `left_at` check) on their NEXT retrieval attempt, so they lose
  RETRIEVAL access to the underlying file, not just thread access. This
  was not true before this slice. See `participant-removal-revocation.md`.
- **Technician tenant-wide `MediaAccessService` behavior for NON-thread-claimed
  assets**: NOT narrowed — an unclaimed `chat_attachment` asset (never
  attached to any thread) is still viewable tenant-wide by
  `tenant_owner`/`staff`/`technician` per `MediaAccessService`'s own
  existing, unmodified policy. This is now a MUCH smaller window than
  before (only unclaimed assets, and only until first use), but is not
  eliminated — see `known-limitations.md`.

## Coverage
Unchanged at 200/226 — this slice deepened the object/attachment/retrieval
policy behind the same 10 already router-guarded routes. See
`canonical-coverage-reconciliation.md`.

## Tests
11 new tests (`tests/test_phase2f18c_platform_notifications_media_sharing_retrieval.py`),
all passing. Combined targeted regression: 344 passed, 0 failed. Full
repository sweep: see `regression-report.md`.

## Final status
**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED** —
see `approval-gate.md`.
