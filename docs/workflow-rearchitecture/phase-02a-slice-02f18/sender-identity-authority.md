# Sender Identity Authority

## Finding: already fully server-derived, no code change required

Every mutation in `provider_router.py`/`staff_router` derives the actor's
identity exclusively from `UserContext` (populated from the verified JWT via
`get_current_user`/the new role dependencies), never from the request body:

- `uuid.UUID(u.user_id)` is passed as `actor_user_id`/`user_id` to every
  service call.
- `RECIP_PROVIDER`/`RECIP_STAFF` (hardcoded Python constants, not
  request-supplied) are passed as `actor_type`.
- `_tid(u)` derives `tenant_id` from `u.tenant_id` (JWT claim).

`SendMsgIn` (the only body model on the sending path) exposes exactly
`message_text`, `message_type`, `visibility`, `media_ids` — no `sender_id`,
`sender_user_id`, `created_by`, or `tenant_id` field exists on it or on
`UpdatePrefIn`/`CreateThreadIn`. Verified directly by
`TestSenderIdentityServerDerived` (checks `model_fields` for the absence of
any identity-override field, not just checks the current handler code).

`ChatMessage.sender_user_id`/`sender_type` and
`NotificationPreference.user_id`/`tenant_id` are written from these
server-derived values inside `chat_service.py`/`notification_service.py` —
confirmed by direct code read, not merely by router inspection.

## System/admin sender identity
`ChatMessageService.add_system_message` (system-authored messages,
`sender_type="system"`) is not reachable from `provider_router.py` at all —
no route in this file can construct a system-authored message. Only
internal/engine callers (e.g. booking confirmation flows) call it directly.
