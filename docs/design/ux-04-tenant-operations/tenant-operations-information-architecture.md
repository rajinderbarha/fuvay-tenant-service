# Tenant Operations Information Architecture

Operations sits alongside UX-03's existing tenant-portal IA (dashboard,
team, pricing, service areas, customers, compliance, media, settings) as a
dedicated operations surface:

```
Operations
├── Command Center (role-sensitive home: today / action queue / dispatch / financial+compliance alerts)
├── Search (unified: booking/job/customer/technician/address/quote/parts/invoice/complaint)
├── Bookings (field_ops.Job pipeline) — list, detail, transition-to-job presentation
├── Jobs (ServiceJob pipeline) — list, detail workspace (status/assignment/inspection/quote/
│         checklist/parts/invoice/credit-commission/communication/media/activity)
├── Complaints & Disputes — case list/detail, dispute presentation (read-only platform authority)
├── Compliance — requirement list/detail/submission workflow (reused from UX-03, extended with
│         changes-requested field-level detail)
└── Staff Operational Home — permission-filtered subset of the above for technician/limited-staff roles
```

Only canonical roles (`tenant_owner`, `staff`, `technician`) compose this
IA differently via `ActionPermissionView` availability — there is no
separate nav tree per role, and nav visibility is never itself an
authorization boundary (server-side permission is authoritative).

Booking and Job remain separate top-level sections, never merged, because
they are separate backend pipelines (`booking-pipeline-preservation.md`,
`job-model-preservation.md`).
