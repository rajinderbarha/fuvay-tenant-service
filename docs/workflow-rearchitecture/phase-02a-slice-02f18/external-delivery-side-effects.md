# External Delivery Side Effects

## Finding: this router has exactly one delivery side effect, and it is safe

`ChatMessageService.send_message` → `_notify_other_participants` writes one
`InAppNotification` row per other active thread participant, synchronously,
in the SAME database transaction as the message itself (before `db.commit()`
— confirmed by direct code read: `db.add(InAppNotification(...))` calls
happen before the single `await db.commit()` at the end of `send_message`).

Consequences:
- **Authorization precedes dispatch**: `validate_thread_access` and the
  (now-enforced) visibility check both raise before any `InAppNotification`
  is constructed — a rejected send produces zero delivery side effect. See
  `no-partial-persistence-delivery-proof.md`.
- **No queue, no worker, no external provider call** exists on this path —
  it is a same-transaction DB insert only. There is nothing here to
  idempotency-guard against duplicate external sends, because there is no
  external send.
- **`CHANNEL_PROVIDERS`** (email/SMS/WhatsApp/push abstractions in
  `channel_providers.py`) are reached only via
  `NotificationService._dispatch_outbox`, which is called only from
  `fire_event`/`dispatch_pending`/`retry_outbox` — none of which is
  reachable from `provider_router.py`. Not in scope to build or harden
  further (OUT OF SCOPE: "Do not add email, SMS or push infrastructure").

## No retry capability on this router
`retry_outbox`/`dispatch_pending`/`retry_failed` are admin-only
(`admin_router.py`, `require_super_admin`) — not reachable here.
