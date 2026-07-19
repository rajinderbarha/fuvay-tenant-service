# Tenant Portal Information Architecture (UX-03)

Nav groups defined in `frontend/tenant-portal/lib/ux03/nav-ia.ts`
(`UX03_NAV_GROUPS`), extending `lib/nav-config.ts`'s `TENANT_NAV_GROUPS`
rather than replacing it (same precedent as UX-02). Not wired into
production `layout.tsx` — see `product-decisions-required.md`.

Groups: Overview, Setup and Profile, Team, Services and Pricing, Service
Areas, Bookings, Jobs, Customers, Quotes and Checklists, Parts and
Inventory, Finance and Credits, Complaints and Support, Compliance, Media,
Reports, Settings, Audit Activity.

Every item carries: label, description, canonical roles (only
`tenant_owner`/`staff`/`technician`), an optional real `permission_key`
(verified against `app/core/permissions.py`), a free-text backend-capability
pointer, a `ReadinessState`, `readOnlyBehavior`, `mobileBehavior`, and an
optional `emptyState` string.

Nav visibility is a UX convenience only — never an authorization boundary.
The backend (`app/core/permissions.py::require_permission`,
`require_tenant_mutation_permission`) is the sole enforcement point. See
`design-governance-rules.md`.

See `tenant-navigation-map.csv` for the flattened per-item table.
