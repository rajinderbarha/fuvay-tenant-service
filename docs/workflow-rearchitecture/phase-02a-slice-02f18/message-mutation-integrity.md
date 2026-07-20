# Message Mutation Integrity

## Ownership
`ChatMessage.thread_id` is always the path-supplied `thread_id`, validated
against a real, resolved `ChatThread` before any write
(`send_message` raises `CHAT_THREAD_NOT_FOUND` otherwise) — unchanged,
pre-existing, confirmed correct.

## Author derivation
`sender_user_id`/`sender_type` are always `actor_user_id`/`actor_type`
(JWT-derived) — see `sender-identity-authority.md`. No edit/delete/move
capability exists anywhere in this router (no `PUT`/`PATCH`/`DELETE` route
on any message) — `moderate_message` (hide) exists in `chat_service.py` but
is reachable only from `admin_router.py`'s `require_super_admin`-gated
route, not from this module.

## Visibility integrity — FIXED this slice
Previously: `visibility` was a fully client-controlled free-text field with
no validation, and an unrecognized value fell open to "visible to
everyone" in `ChatMessage.is_visible_to`. Fixed:
1. `send_message` now rejects any `visibility` value outside
   `{thread, admin_only, provider_only, customer_only}`
   (`CHAT_MESSAGE_INVALID_VISIBILITY`).
2. A non-admin sender (provider/staff/technician/customer) may only send
   with `visibility="thread"` — cannot mark their own message
   `admin_only`/`provider_only`/`customer_only`.
3. `is_visible_to`'s fallback for any (now theoretically unreachable, but
   defense-in-depth for direct DB writes or future callers) unrecognized
   value fails closed (`admin`-only) instead of open (`True`).

## Read receipts
`ChatMessageRead.user_id` is always `actor_user_id` (JWT) —
`mark_thread_read` cannot mark another user's message read; there is no
`user_id` field on any request body on this path — unchanged, confirmed.

## Closed/terminal thread behavior
`send_message` already rejects sends into `TERMINAL_THREAD_STATUSES`
(`closed`/`archived`/`blocked`) with `CHAT_THREAD_CLOSED` — pre-existing,
unchanged, confirmed still enforced (validated before the new visibility
check, so a closed thread still fails first).

## Attachments
`media_ids`/`media_urls` remain unvalidated opaque JSONB (no ownership/type
check against a media engine) — this is a genuine open gap, but building
media-asset-ownership validation would require reaching into another
engine's data model with no existing dependency for it; documented in
`known-limitations.md` rather than built ad hoc (OUT OF SCOPE: "Do not
build attachment infrastructure").
