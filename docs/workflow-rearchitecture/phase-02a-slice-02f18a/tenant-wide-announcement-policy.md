# Tenant-Wide Announcement Policy

## Finding: no such capability exists — re-confirmed, not newly discovered

2F-18's `bulk-broadcast-safety.md` already established that no bulk/broadcast
capability exists anywhere in `provider_router.py`. This slice's mission
explicitly asks whether any technician-accessible capability is a
"tenant-wide announcement" — re-examined against the FULL route set
(including `staff_notif_router`/`staff_chat_router`, `customer_router.py`)
and confirms: **none of the 24 routes in this module's provider/staff/
customer surface creates, sends, or administers a tenant-wide announcement.**
`mark_all_read` is the only "all X" verb, and it is principal-scoped (see
`recipient-owned-notification-actions.md`), not a broadcast to other users.

`NotificationEventRegistry`/`fire_event` (the actual event-firing mechanism
used by OTHER engines to notify e.g. "job assigned" to potentially many
recipients) is not reachable from any router in this module and was
correctly out of scope for both 2F-18 and this slice.

## Conclusion
Every technician-accessible route is classified `TECHNICIAN_DIRECT_RECIPIENT_ONLY`
or `TECHNICIAN_ASSIGNED_SERVICEJOB_ONLY`/`TECHNICIAN_ACTIVE_PARTICIPANT_ONLY`
(see `technician-capability-matrix.csv`) — none is
`TENANT_WIDE_TECHNICIAN_ANNOUNCEMENT`, because that capability does not
exist to classify. This workstream's "preserve legitimate tenant-wide
announcements where directly proven" instruction has no applicable target
in this module.
