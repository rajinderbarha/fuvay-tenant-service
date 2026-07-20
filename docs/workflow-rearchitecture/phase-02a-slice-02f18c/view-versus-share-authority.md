# View Versus Share Authority

## The distinction the mission requires
- `may_view_asset`: can this principal fetch/see this specific asset AT
  ALL? — this is exactly what `MediaAccessService.assert_can_view` proves,
  and only this.
- `may_attach_asset` (redistribution into a NEW context): can this
  principal SHARE this asset into a specific conversation, making it
  visible to everyone who can read that conversation (who may be a
  DIFFERENT audience than whoever the asset's original tenant/customer
  scoping alone would authorize)?
- `may_receive_asset` (recipient authority): can EVERY member of the
  target audience actually access it?

2F-18B treated `may_view_asset` (the sender's own view authority) as
sufficient for `may_attach_asset` — the mission is correct that these are
NOT equivalent in general. This slice closes the gap specifically for the
dimension where it mattered most in practice: SAME-CUSTOMER,
CROSS-CONTEXT reuse (the thread-claim lock), which is the concrete case
where a sender's OWN view authority (satisfied — same tenant/customer)
did not imply the asset was appropriate to attach to THIS particular
conversation.

## What `MediaAccessService` proves and does not prove
| Question | Proven by `assert_can_view`? |
|---|---|
| Principal view authority (can THIS user see THIS asset) | YES |
| Redistribution authority (can THIS user SHARE it into a NEW conversation) | NO — not modeled at all |
| Recipient authority (can OTHER users in the target audience see it) | NO — the check is single-principal, not audience-aware |
| Visibility compatibility (message visibility vs. asset visibility) | NO — `MediaAsset` has no visibility enum comparable to `ChatMessage.visibility` |
| Conversation context (is this the "right" conversation for this asset) | NO — no thread/conversation concept exists in `access.py` at all |
| Job context (is this the "right" Job for this asset) | NO — no Job concept exists in `access.py` at all |
| Revocation behavior (does removal from a group revoke this) | NO — `access.py` re-evaluates fresh every call, but only against static tenant/customer/uploader fields, nothing conversation-scoped |

## Composed chat-attachment policy implemented this slice
`assert_can_view` was NOT modified (would ripple across every media
context app-wide). Instead, a narrow, ADDITIONAL, chat-specific composed
policy layers on top, entirely within `platform_notifications` (send-time,
`chat_service._validate_attachments`) and a small, scoped addition to
`MediaAssetService` (retrieval-time, `_assert_chat_thread_authority`,
gated strictly to `media_context == "chat_attachment"`):

1. `assert_can_view` (existing) — sender's OWN view authority. Necessary,
   not sufficient (per this slice's own framing).
2. `media_context == "chat_attachment"` (2F-18B) — asset is permitted for
   chat use at all.
3. Tenant + customer match (2F-18A/B) — asset belongs to the right
   tenant/customer.
4. **Thread-claim lock (this slice)** — asset is not already claimed by a
   DIFFERENT conversation; first successful use claims it for THIS one.
   This is the closest approximation of "conversation context" achievable
   without a schema change.
5. **Retrieval-time thread authority (this slice)** — for a CLAIMED asset,
   every future retrieval (not just the original send) re-validates
   against the SAME thread-authority rule the message itself required —
   this is the closest approximation of "recipient authority" achievable:
   rather than checking every recipient AT SEND TIME, every recipient's
   OWN retrieval is gated at RETRIEVAL TIME by the identical rule.

This composition is intentional: checking "can every intended recipient
receive this" exhaustively at send time would require enumerating and
re-validating every current thread participant (expensive, and largely
redundant — see `attachment-recipient-authority.md`); checking it at
EVERY retrieval instead means the check is inherently always fresh
(handles participants added/removed after the message was sent) and never
skipped.
