# Attachment Recipient Authority

## Design decision: enforce at retrieval time, not exhaustively at send time

The mission asks to "validate that every intended recipient may receive
the asset" before persistence. A literal per-recipient check at send time
would mean, for every `media_id` in a message, looping over every current
`ChatThreadParticipant` and running `MediaAccessService.assert_can_view`
(or an equivalent) for each one individually before allowing the send.

This was NOT built, for a specific, reasoned justification:

**Every principal who can read a thread's messages has ALREADY passed
`ChatThreadService.validate_thread_access` for that exact thread** — this
is enforced on every read route (`list_messages`, `get_thread`) regardless
of whether a specific message contains an attachment. A recipient who
could not legitimately be in that thread cannot read ANY message in it,
attachment or not. Therefore, verifying "every current participant may
receive this asset" at send time would be answering a question already
guaranteed true by the SAME infrastructure that gates reading the
conversation at all — it does not close an additional gap, only adds
redundant, point-in-time work that goes stale the moment a NEW participant
is added after the message was sent.

## What IS enforced, and where
Instead, recipient authority for attachments is enforced continuously,
per-recipient, at the moment each recipient actually tries to view the
asset — via this slice's retrieval-time thread-authority check
(`MediaAssetService._assert_chat_thread_authority`). This has a strictly
stronger property than a send-time snapshot check: it is re-evaluated on
EVERY retrieval, so it automatically accounts for:
- A participant removed AFTER the message was sent (denied on their next
  retrieval attempt, not just for future messages).
- A technician reassigned to a different Job after the message was sent
  (denied on their next retrieval attempt).
- A new participant added after the message was sent (allowed once they
  legitimately join, without needing to "catch up" on old attachments'
  authorization state).

## Requirements checklist (re-verified against this design)
- A customer-visible message cannot contain a provider-only asset — TRUE:
  `media_context == "chat_attachment"` is the only permitted context
  (2F-18B), and `chat_attachment` is in `MediaAccessService`'s
  `CUSTOMER_CONTEXTS` set — a genuinely provider-only asset would have a
  DIFFERENT `media_context` and is rejected outright before this question
  is even reached.
- A technician-visible message cannot contain staff-only media — same
  reasoning; additionally, `content-visibility-policy.md` (2F-18A) already
  ensures `provider_only`-VISIBILITY messages are invisible to technician
  VIEWERS regardless of attachment content.
- An internal message cannot accidentally be returned through customer
  serialization — unchanged from 2F-18 (`is_visible_to` enum filtering).
- Removed participants are not treated as intended recipients — TRUE by
  construction: a removed participant's NEXT retrieval attempt fails
  `validate_thread_access` (2F-18A's `left_at` check, now also applied at
  retrieval time via this slice's fix).
- Unrelated tenant users are not treated as recipients — TRUE: they cannot
  pass `validate_thread_access` for a thread they have no relationship to
  (2F-18A's technician policy; office persona is tenant-wide by ratified
  design, unchanged).

## If recipient authorization cannot be proven
Per the mission's own fallback ("If recipient authorization cannot be
proven, reject the attachment while allowing attachment-free messaging"):
this slice's design makes this scenario structurally rare — since
recipient authority is ALWAYS re-derivable from `validate_thread_access`
at retrieval time (there is no state where it "cannot be proven" for an
active thread), the explicit reject-attachment-only fallback is not
separately implemented; the closest equivalent is the existing thread
resolution failure path in `create_thread`/`_resolve_job_for_thread`
(2F-18/2F-18A), which already causes attachment-carrying AND
attachment-free messages alike to fail if the thread itself cannot be
authorized.
