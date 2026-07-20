# Product Decisions Required

These are flagged for the SELECTED module's implementation slice (2F-20),
not resolved here (discovery/selection only).

## 1. Should `staff` be admitted alongside `tenant_owner` for compliance capabilities?
Current `require_tenant_owner` (and the recommended drop-in replacement,
`require_tenant_owner_mutation`) excludes `staff` entirely. **Question for
product/legal**: should office staff be permitted to create/cancel DPDP
requests, respond to customer/staff DPDP correspondence, or withdraw
consent on the tenant's behalf, or is this an owner-only regulatory
responsibility by design?

## 2. Export generation rate-limiting/throttling policy
`generate_export` currently has no rate limit at the route level (unlike
`create_my_request`, which has an explicit 10/day cap via
`ComplianceAuditLog` count). **Question for product**: should export
generation carry its own throttle, given each export represents a
potentially large PII extraction?

## 3. Location and audit of the out-of-router export-generation worker
This slice's investigation confirmed `generate_export` only QUEUES a
`ComplianceExport` row (`status="processing"`) — the actual PII
aggregation and file generation happens in a process not located during
this investigation. **Question for product/engineering**: where does this
worker live, and should its own authorization/tenant-scoping be audited
as part of Slice 2F-20, or does it operate purely off the already-scoped
`ComplianceExport.request_id` FK (making it structurally safe regardless
of where it runs)?

## 4. Non-selected module bundling recommendations
The queue recommends bundling `admin_catalog_brand`/`recommendation`/
`service_option` together (ranks 6-8) and `media.new_router`
profile-routes with `profile.router` (ranks 4-5) for future slices, given
their small size and shared "self-owned by construction" risk profile.
**Question for product**: confirm these bundling recommendations before a
future slice acts on them, since bundling decisions affect slice sizing
and sequencing.
