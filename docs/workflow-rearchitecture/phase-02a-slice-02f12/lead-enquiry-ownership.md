# Lead/Enquiry Ownership — Slice 2F-12 (Workstream 7)

## Not applicable in this router as a separate "lead" record
`execution.coaching_router` operates directly on `CoachingAppointment` —
already a confirmed, specific appointment, not a pre-conversion lead or
enquiry record (unlike `execution.real_estate_router`'s `RealEstateLead`,
which represents an unconverted lead throughout its lifecycle). There is
no separate "coaching lead" or "student enquiry" model in this router's
reach — the closest analogous pre-confirmation record
(`CoachingAppointmentDraft`) lives in the distinct `coaching_appointment`
module (see `alternate-coaching-route-audit.md`), out of this router's
scope.

## What this means for Workstream 7's requirements
- **Appointment belongs to the tenant**: enforced (see
  `tenant-customer-authority-boundary.md`).
- **Student/customer association cannot be changed**: no route in this
  router accepts a `customer_id` field at all — the customer association
  is fixed at draft-confirmation time, entirely outside this router's
  reach.
- **Assignment cannot target a foreign-tenant user**: no assignment
  *creation* route exists in this router at all — `staff_member_id` is
  already set on the `CoachingAppointment` record before any route in
  this module is reached (assignment happens upstream, out of scope,
  same as real estate's `agent_id`).
- **Technician cannot enumerate all appointments**: technician is now
  denied at the persona layer for every route in this module (fixed
  this slice).
- **Customer cannot perform provider-side transitions**: structurally
  impossible — `customer_router` has exactly one route, read-only.
- **Provider cannot fabricate customer acceptance**: there is no
  "customer accepted" concept in `APPT_TRANSITIONS` at all — every
  transition is staff/provider-actor-only.
- **Direct ID substitution cannot bypass filtering**: tenant/customer
  filters are applied in the actual query construction, re-verified
  directly.
- **Notes and contact history remain tenant-private**: `get_notes`
  filters by `tenant_id`; customer path uses `customer_only=True`.
- **Customer-facing tracking excludes provider-internal notes**: same
  mechanism as real estate — `customer_tracking` never calls
  `get_timeline` at all.
