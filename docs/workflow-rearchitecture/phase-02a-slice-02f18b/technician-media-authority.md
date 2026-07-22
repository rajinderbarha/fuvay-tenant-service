# Technician Media Authority

## Verified
- **Technician thread access remains assignment/participant limited** —
  unchanged from 2F-18A; `send_message`'s attachment check runs strictly
  AFTER `validate_thread_access`, so a technician who cannot even reach
  the thread never has their attachment evaluated at all.
- **Assignment to Job A does not authorize Job B media** — indirectly true
  by construction: a technician assigned only to Job A cannot pass
  `validate_thread_access` for Job B's thread in the first place (2F-18A),
  so no attachment check for Job B's thread is ever reached by that
  technician.
- **Tenant membership alone does not authorize generic tenant media** —
  TRUE for non-`chat_attachment`-context assets (rejected by the context
  check regardless of role) and TRUE for the thread-access gate itself
  (2F-18A). PARTIALLY true for `chat_attachment`-context assets
  specifically: `MediaAccessService`'s EXISTING policy grants
  `tenant_owner`/`staff`/`technician` visibility into ANY customer-context
  asset in their own tenant — this is broader than the Job-assignment
  policy this module's THREAD access uses, but it is the established,
  reused-not-modified media-engine-wide policy (see
  `known-limitations.md`). Documented explicitly via
  `test_technician_can_view_same_tenant_customer_context_asset` rather
  than silently assumed away.
- **Another technician's private/internal upload is not automatically
  usable** — if that technician's upload has `media_context` outside
  `CUSTOMER_CONTEXTS`/`PARTICIPANT_CONTEXTS` (e.g. an internal-only
  context not in either set), `assert_can_view`'s non-customer-context
  branch still requires tenant match — same-tenant technicians CAN view
  each other's non-customer-context, same-tenant uploads under the
  existing policy (again, existing/reused, not narrowed).
- **Removed participants cannot retrieve conversation media** — enforced
  at the THREAD level (2F-18A's `left_at` check blocks
  `send_message`/`list_messages`/`get_thread` entirely for a removed
  participant); the media engine's own retrieval routes do not know about
  chat-thread participation at all (media access is thread-INDEPENDENT,
  governed solely by `MediaAccessService`), so a removed participant who
  still knows a `media_id` from before removal and separately has generic
  tenant-role media access COULD still retrieve the raw file via
  `/v1/media/{id}/view` even after losing thread access — this is a
  genuine, narrow residual gap (media access and thread access are two
  independent authorization systems that don't share revocation state) —
  flagged in `known-limitations.md`, not fixed (would require modifying
  the general media engine).
- **Completed/cancelled Job handling follows the currently ratified thread
  access behavior without silently broadening media access** — confirmed:
  no code path in this slice treats a completed Job's assets any
  differently than an in-progress Job's.

## Not invented
No technician-wide media capability was added. Every technician media
interaction in this slice's test suite goes through the SAME
`MediaAccessService.assert_can_view` call as every other persona — no
technician-specific branch was created in `_validate_attachments`.
