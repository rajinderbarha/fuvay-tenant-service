# Quote/Checklist/Parts Verification (Workstream 7)

Not attempted this round. The E2E proof job (`JOB-20260721-000008`) was
carried only through `accepted` status this round — the next real legal
transitions per `mobile/staff-app/src/lib/transitions.ts`
(`onTheWay` -> `reachedSite` -> `startInspection` -> ... -> quote/parts
requests) were not exercised. This is a real, valid resumption point for a
future round: the exact job/booking/tenant/technician IDs are recorded in
`real-record-evidence.csv` and can be picked up directly without recreating
the booking.

Canonical rule to preserve when this is picked up: PartsRequest is
ServiceJob-only, technician requests/views only, provider/tenant
approves/rejects/records-installation, technician NEVER marks installed
(per this phase's hard constraints).
