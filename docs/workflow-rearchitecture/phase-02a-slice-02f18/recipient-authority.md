# Recipient Authority

## Notification read/mark-read routes
No route accepts a recipient identifier at all — every read/mark-read call
is implicitly "for the caller" (`user_id = uuid.UUID(u.user_id)`, JWT
derived). There is no notification-creation or -send capability anywhere in
`provider_router.py` (event firing/outbox creation is internal-only, called
by other engines via `NotificationService.fire_event`, never exposed as an
HTTP mutation on this router). Arbitrary recipient targeting is therefore
structurally impossible on this router — not merely denied, but absent.

## Chat thread/message routes
The only "recipient-adjacent" input is `CreateThreadIn.record_id` (which
record to attach a conversation to) — this is a record reference, not a
literal user/recipient ID. Fixed this slice: `chat_service.create_thread`
now enforces that a resolvable `record_id` (`service_booking`,
`service_job`, `complaint`) both exists and belongs to the caller's own
tenant (provider/staff) or is genuinely the caller's own record (customer),
before any thread is created. See `no-partial-persistence-delivery-proof.md`
for the negative-path proof.

Once a thread exists, its recipient set (`ChatThreadParticipant` rows) is
derived entirely server-side: the tenant owner + assigned staff (from the
linked record) are auto-added on creation (`_provider_participants`); no
caller (provider, staff, or customer) can add/remove participants from
`provider_router.py` — no such route exists here (participant management
is not implemented anywhere in this codebase yet, not just absent from this
router — confirmed by grep across `chat_service.py`).

## Device tokens / arbitrary external addresses
Not present anywhere in this module — no device-token or external-address
field exists on any request schema in this router.
