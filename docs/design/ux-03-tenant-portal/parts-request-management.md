# Parts Request Management

`PartsRequestFixture.serviceJobId` always references a `ServiceJobFixture`
id (never a `BookingFixture`/`field_ops.Job` id) — enforced by
`permissions-and-pipelines.test.ts`.

Authority model:
- Technician (`role: "technician"`, permission `field_ops:parts:add`):
  request parts on own jobs, view request status. No approve/reject/install
  action is ever rendered for a technician.
- Provider-side staff/owner with `inventory:items:write`: approve, reject,
  or mark-installed. `PartsRequestFixture.decidedByStaffId` is null until a
  staff/owner decision is recorded.

The dev showcase (`/dev/ux-03/parts-approval`) renders Approve/Reject/Mark
Installed buttons disabled with a `MOCK_DESIGN_ONLY` note — no technician
install authority is ever exposed, matching the hard constraint in the task
brief.
