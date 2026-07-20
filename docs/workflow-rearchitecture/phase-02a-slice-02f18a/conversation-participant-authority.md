# Conversation Participant Authority

## Active participant definition (tightened this slice)
Previously, the generic ("anyone else must be a participant") fallback
branch in `validate_thread_access` checked for ANY participant row
regardless of `left_at` — a removed participant (`left_at` set) would still
pass. Fixed this slice: both the new `RECIP_TECHNICIAN` branch's
participant fallback AND the generic fallback now filter
`ChatThreadParticipant.left_at == None` — a removed participant is denied
(`test_removed_participant_technician_denied`).

## Verified
- Acting principal has an ACTIVE participant row (not merely any historical
  row) — fixed and tested this slice.
- Participant belongs to the exact conversation (`thread_id` filter,
  unchanged, pre-existing).
- Duplicate participants: `_add_participant` dedupes on `(thread_id,
  user_id)` before insert — pre-existing, unchanged, re-confirmed by
  code read.
- Conversation visibility matches participant type: enforced by
  `ChatMessage.is_visible_to(viewer_type)` — now correctly receives
  `"technician"` as a distinct `viewer_type` for technician callers (see
  `content-visibility-policy.md`), rather than being conflated with
  `"staff"`.

## Not changed this slice (no capability exists to test)
- Participant ADD/REMOVE routes: still absent from this router entirely
  (confirmed absent in 2F-18, re-confirmed unchanged) — "one participant
  cannot add arbitrary users" / "technician cannot add unrelated
  participants" are structurally true because NO participant-mutation route
  exists anywhere reachable from `provider_router.py`, `staff_chat_router`,
  or `customer_router.py`. Not a gap; a genuinely absent capability.
- Cross-tenant participant rejection: participants are seeded exclusively
  server-side by `_provider_participants`/the creator's own identity — no
  route accepts a participant list, so cross-tenant participant injection
  is structurally impossible, not merely denied.

## A same-tenant user is not automatically a participant
True for `RECIP_TECHNICIAN` as of this slice (the core fix). Still FALSE
for `RECIP_PROVIDER`/`RECIP_STAFF` by ratified office policy — tenant
membership IS sufficient for the office/owner persona, which is the
intentional, documented `STAFF_INTERNAL_CONVERSATION` tenant-wide policy
(unchanged, not a technician-equivalent gap — office staff/owners are
expected to have oversight of all their tenant's customer conversations).
