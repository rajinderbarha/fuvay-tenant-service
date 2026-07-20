# Participant Removal Revocation

## Corrected classification from 2F-18B
2F-18B classified this as a pure PRODUCT_POLICY item. This slice's mission
explicitly lists "The classification of participant-removal media access
as product-only" among the claims requiring correction. Corrected: for
CLAIMED `chat_attachment` assets, removal now HAS a real, enforced
consequence at the media layer, not just the thread layer.

## Verified sequence (Workstream 7's exact test scenario)
1. **Before removal**: an active participant can read the thread
   (`validate_thread_access` passes) and, if a message in it has a
   `chat_attachment`, can retrieve the underlying file (this slice's
   `_assert_chat_thread_authority` passes, since `validate_thread_access`
   passes).
2. **Participant is removed** — `ChatThreadParticipant.left_at` is set
   (existing mechanism, not built this slice — no participant-removal
   ROUTE exists anywhere in this module, confirmed unchanged since 2F-18;
   this is about what happens once a row's `left_at` IS set, by whatever
   internal/future mechanism sets it).
3. **Participant cannot read the thread** — `validate_thread_access`'s
   generic fallback and `RECIP_TECHNICIAN` branch both filter
   `left_at == None` (2F-18A) — TRUE, unchanged.
4. **Participant cannot read future messages** — same mechanism, TRUE,
   unchanged.
5. **Participant cannot retrieve private attachment content through a
   direct media route** — **THIS SLICE's fix**: previously FALSE (a
   removed participant who still knew a `media_id` and separately had
   generic tenant-role or "own upload" view rights via
   `MediaAccessService` could still fetch the raw file — the two
   authorization systems didn't share revocation state, as documented in
   2F-18B's `known-limitations.md` item 4). Now TRUE for CLAIMED
   `chat_attachment` assets: retrieval re-runs `validate_thread_access`,
   which denies a removed participant identically to thread access.

## Tenant membership alone does not override removal
Confirmed: `validate_thread_access`'s office (`RECIP_PROVIDER`/`RECIP_STAFF`)
branch is tenant-wide by ratified design (unchanged) — a removed
participant who is ALSO a `tenant_owner`/`staff` member of the owning
tenant regains access via the OFFICE persona's own tenant-wide rule, not
because their removed participant row is ignored. This is intentional and
consistent: office oversight is tenant-scoped, not participant-scoped, by
design (2F-18A) — removal from a thread as a PARTICIPANT does not (and
should not) revoke an office user's independent, tenant-wide oversight
authority. Only `RECIP_TECHNICIAN` and generic (non-office, non-customer)
callers are actually gated by the participant row at all, so removal is
only a meaningful revocation event for those personas — documented, not a
gap.

## What remains a residual gap
An UNCLAIMED asset, or a NON-`chat_attachment`-context asset referenced
directly by ID, is unaffected — this fix is scoped exactly to the
chat-attachment retrieval chain this slice's mission covers, not a
general media-engine-wide revocation model.
