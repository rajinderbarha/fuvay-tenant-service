# field_ops.Job Detail Specification

Corrects UX-04A's wrong NOT_APPLICABLE disposition. Fields: job id
(`field_ops.Job` canonical id), model label ("field_ops.Job"), source
Booking id, customer, service, schedule, address, assigned staff, status,
SLA, timeline, notes, activity/audit, available/restricted actions.
Deliberately excludes (real repository evidence, per
`booking-job-pipeline-separation.md`): PartsRequest, inspection,
checklist, quote, commission — `field_ops.Job` has none of these concepts.
Loading/empty/error states are not separately built this pass (the route
renders one populated fixture) — see `known-limitations.md`.
