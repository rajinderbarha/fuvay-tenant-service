# Tenant Detail Page Pattern

`components/ux03/patterns/TenantDetailPage.tsx` — header + badges + a
section-nav sidebar + active-section content pane. Used by Job Detail
(overview/customer/assignment/quote/parts/finance/activity sections).
Callers supply a `DetailSection[]` array; the pattern owns active-section
state.
