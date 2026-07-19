# Tenant 360 Specification

Component: `EnterpriseDetailPage` instantiated in
`app/dev/ux-02/tenants/[id]/page.tsx`. Readiness: `MOCK_DESIGN_ONLY` (aggregates several
engines, most not yet wired to real endpoints for this view).

## 15 sections (sticky nav desktop, `<select>` jump on mobile)
1. Overview — legal name, vertical, status, created date.
2. Owner & Contacts — name, email.
3. Plan & Package — package name, package credit balance, commission rate.
4. Security Deposit — amount held; explicitly labeled separate from package credit and not payable
   to platform for ordinary job payments (canonical finance rule).
5. Storage — used/quota GB.
6. Staff — staff count.
7. Serviceability — region/city.
8. Bookings — placeholder (MOCK_DESIGN_ONLY).
9. Invoices — placeholder (MOCK_DESIGN_ONLY).
10. Complaints — open complaint count.
11. Compliance Cases — tenant-scoped cases from fixtures.
12. Verification — placeholder linking conceptually to the Verification Review workspace.
13. Reviews & Ratings — placeholder.
14. Notifications — placeholder.
15. Audit Trail — tenant-scoped audit entries from fixtures.

## Readiness per section
Sections backed by real `TenantFixture` fields (1,2,3,4,5,6,7,10,11,15) are closer to
`READ_ONLY_READY` once wired to real endpoints; sections 8/9/12/13/14 are placeholders pending a
confirmed data source — flagged `MOCK_DESIGN_ONLY` throughout, not silently implied as complete.

## Mobile
`EnterpriseDetailPage` swaps the sticky left nav for a single `<select>` under 768px.
