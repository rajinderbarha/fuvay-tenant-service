# Typed Fixture Contract

`frontend/tenant-portal/lib/ux03/types.ts` declares one interface per
entity (TenantProfile, StaffPermission, TeamMember, Booking, ServiceJob,
PartsRequest, PackageCredit, SecurityDeposit, FinanceTransaction, Pricing,
ServiceArea, Customer, Complaint, ComplianceItem, MediaAsset, AuditEvent).
`fixtures.ts` provides one concrete, realistic instance set per interface
(home_services vertical, Bengaluru-based, no lorem ipsum, no real secrets,
no real production URLs — `previewToken`/`correlationId`-style placeholder
strings only). Every fixture entity is explicitly documented as a UI-layer
model, not a second source of truth for the backend schema.
