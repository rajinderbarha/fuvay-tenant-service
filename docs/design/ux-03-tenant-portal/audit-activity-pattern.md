# Audit / Activity Pattern

`/dev/ux-03/audit-activity` — `TenantListPage` over `AuditEventFixture`,
tenant-scoped only. Never renders platform-wide events, other tenants'
events, secrets, or tokens — enforced by the fixture type itself having no
such fields.
