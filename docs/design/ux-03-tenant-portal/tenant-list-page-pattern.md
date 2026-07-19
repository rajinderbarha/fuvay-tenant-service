# Tenant List Page Pattern

`components/ux03/patterns/TenantListPage.tsx` — header + optional search +
`DataTable` (loading/error/empty states from the design system). Used by
Booking List, Job List, Team List, Finance History, Service Areas,
Pricing, Audit Activity. Generic over row type `T`; callers supply columns,
rowKey, and an optional search predicate.
