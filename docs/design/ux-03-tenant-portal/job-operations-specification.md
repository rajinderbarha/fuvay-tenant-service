# Job Operations Specification

ServiceBooking -> ServiceJob pipeline. List (`/dev/ux-03/job-list`) and
detail (`/dev/ux-03/job-detail`) preserve `canonicalId` (the real
`ServiceJob` id). Detail sections: overview, customer + address,
assignment, quote, parts (ServiceJob-only — see parts-request-management.md),
finance (commission/credit — see package-credit-commission-pattern.md),
activity. Statuses: quoted, scheduled, in_progress, awaiting_parts,
completed, cancelled. Same unresolved-cancellation constraint as bookings.
