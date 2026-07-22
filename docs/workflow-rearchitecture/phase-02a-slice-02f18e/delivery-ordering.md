# Delivery Ordering

## Re-traced, unchanged from 2F-18/2F-18C
`_notify_other_participants` (the only delivery-adjacent call reachable
from this module — writes `InAppNotification` rows) still executes AFTER
ALL of: thread authority, attachment validation (including this slice's
office first-use ambiguity check and the retrieval lifecycle check — the
latter is retrieval-only, not attach-time, so does not apply here but is
consistent in spirit), and claim assignment — and strictly BEFORE
`db.commit()`.

## Required proofs (Workstream 7)
- **Authorization precedes dispatch** — TRUE, unchanged. Every
  authorization check (thread, media, office first-use) raises before
  `_notify_other_participants` is ever called.
- **Attachment validation precedes dispatch** — TRUE, unchanged.
- **Claim/message commit precedes dispatch where established** — this
  module's ONLY "dispatch" is the `InAppNotification` DB row write, which
  happens BEFORE `db.commit()`, not after — i.e., dispatch and the
  claim/message write are part of the SAME commit, not sequenced
  commit-then-dispatch. This is consistent with `DATABASE_ONLY_NOTIFICATION_RECORD`
  (below) — there is no EXTERNAL dispatch to sequence after commit,
  because there is no external dispatch at all.
- **Rollback produces no queued work** — TRUE — there is no queue; a
  rollback undoes the `InAppNotification` row write along with everything
  else in the same transaction (same mechanism as the message and claim).
- **A losing concurrent claim produces no delivery** — TRUE — a losing
  claim never reaches `_notify_other_participants` at all (the conflict
  check raises before message construction, which is before
  `_notify_other_participants` is called).
- **Client cannot influence delivery destination or credentials** — TRUE,
  unchanged — `_notify_other_participants` iterates `ChatThreadParticipant`
  rows (server-resolved, not client-supplied) to determine recipients; no
  destination/credential field is ever client-controlled.

## `DATABASE_ONLY_NOTIFICATION_RECORD` — confirmed, unchanged
Re-verified this slice: no email/SMS/push/WebSocket/queue integration
exists anywhere reachable from `provider_router.py`, `customer_router.py`,
or the attachment/claim chain. The ONLY delivery side effect on this
entire module remains the synchronous, same-transaction `InAppNotification`
row write.
