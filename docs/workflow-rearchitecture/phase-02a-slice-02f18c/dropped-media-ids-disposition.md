# Dropped media_ids Disposition

## Disposition chosen: SAFE_SUPPORT

`staff_send_message`'s `SendMsgIn.media_ids` was accepted by the schema
but never forwarded to `ChatMessageService.send_message` — silently
discarded (not insecure, since nothing was ever processed, but a genuine
functional gap the mission flags as unacceptable: "Do not silently ignore
client attachment input").

**SAFE_SUPPORT was chosen over REJECT_AS_UNSUPPORTED** because the full
validation infrastructure required to support it safely already exists
(built in 2F-18B/2F-18C) and is already used by the sibling
`provider_send_message` route — wiring it up required no new validation
logic, only forwarding the already-parsed field:

```python
media_urls = {"media_ids": body.media_ids} if body.media_ids else None
msg = await _msg_svc.send_message(
    ..., media_urls=media_urls, actor=u,
)
```

## Consequence
`staff_send_message` (both `staff` and `technician` callers, via
`_staff_guard`) now runs attachments through the IDENTICAL validation
chain as `provider_send_message`: existence, lifecycle, `media_context`
taxonomy, tenant match, customer match, `MediaAccessService.assert_can_view`,
and the thread-claim lock — all six checks, not a subset.

## No new table or migration
The relationship is persisted via `ChatMessage.media_urls` (existing
JSONB column, unchanged schema) exactly as `provider_send_message` already
does — no new table, no migration.

## `customer_router.py` — not applicable
`customer_router.py`'s `SendMessageIn` has no media field at all (confirmed
in 2F-18B's `attachment-route-inventory.csv`, re-confirmed this slice) —
there is no "dropped" field to resolve there; it was never accepted in the
first place.
