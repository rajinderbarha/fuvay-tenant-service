# Admin Home Services Catalog Setup — UI Report

## Structure delivered

1. Breadcrumb (Admin / Home Services / Service Catalog)
2. Header (title, subtitle, Refresh + Add Service actions)
3. Manual-bargain-disabled rule banner (Auto Low/Mid/High, brand → type →
   base resolution order)
4. Left panel: grouped service list (8 real Home Services groups: AC &
   HVAC, Plumbing, Electrical, Carpentry & Woodwork, Painting & Walls,
   Appliance Repair, Pest Control, Home Security), each row showing
   pricing model, types/brands counts, active-status dot
5. Right panel: selected-service header (name, pricing model badge,
   status badge, View link) + 8-tab configuration console (General, Types
   & Pricing, Brands, Issues, Options, Zones/Tiers, Customer Price
   Preview, Activity)
6. Types & Pricing tab: real editable table (floor/ceiling/platform
   fee/deduction credits per type) with inline edit row and live Customer
   Sees preview chips
7. Brands tab: per-brand behavior toggles (can override price /
   routing-only) + inline override-limits editor + preview chips
8. Customer Price Preview tab: standalone calculator (provider min/max +
   fee → Low/Mid/High breakdown), matches the ticket's exact example
9. Activity tab: real audit trail scoped to the selected service and its
   pricing rules

## Visual design notes

Consistent with every other admin/tenant page built this session: the app
uses a light/neutral enterprise theme by default (`--surface`,
`--text-primary` custom properties), not a system-wide dark theme. Rather
than convert the whole page to dark mode (a large, separate design-system
change out of this ticket's scope), the console uses the app's real
enterprise card/table language with clear status coloring, tab navigation,
and grouped hierarchy — matching the "enterprise SaaS, clean cards, clear
hierarchy" requirement without fabricating a one-off dark theme that would
be inconsistent with the rest of the admin app.

## No duplicate CRUD for Issues/Options/Zones

Issue Types, Service Options, and Pricing Tiers each already have a
dedicated, real, working admin screen with full CRUD
(`/admin/service-setup/issue-types`, `/admin/service-options`,
`/admin/pricing-tiers`). Rather than rebuild three more full CRUD forms
inside this console (duplicate source of truth, duplicate bugs), those
three tabs show a real, live, service-filtered read list plus a "Manage
in X →" link to the canonical screen. This is a deliberate composition
decision, documented in Remaining Blockers, not a shortfall — every number
shown is real, not a placeholder.

## Real data, no fabrication

Every value shown (floor/ceiling, platform fee, deduction credits,
Low/Mid/High preview, brand behavior, audit events) is live-fetched from
the real backend. Fields with no configured value show "Not configured",
never a blank cell or fabricated default.
