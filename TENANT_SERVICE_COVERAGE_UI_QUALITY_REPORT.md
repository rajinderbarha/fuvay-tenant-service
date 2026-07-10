# Tenant Service Coverage Areas — UI Quality Report

## Structure delivered (matches the reference description)

1. Breadcrumb (Tenant Portal / Setup / Service Coverage Areas)
2. Enterprise header (title, subtitle, Refresh + Add Service Area actions)
3. Coverage Readiness Hero: dark gradient card (`#1e293b` → `#0f172a`),
   status/badge pair (Coverage Ready / Not Ready / Needs Attention), 4 meta
   chips (Active Areas, Slots Used, Primary Area, Remaining Slots), circular
   slots-used progress ring, information banner
4. KPI card row (Total Areas, Primary Area, Coverage Health, Validation
   Issues) — gradient icon blocks, status-colored
5. Action Required panel — per-issue card with a real action button (Add
   Area / Set Primary), or an all-clear success banner
6. Two-column layout: Coverage Areas table (search + Active/Inactive tabs,
   10 real columns, row actions) on the left; Coverage Summary, Coverage
   Rules, and Recent Activity cards stacked on the right
7. Add Service Area drawer/modal: subtitle, Area Type selector, Location
   Details, live Validation Preview (real backend call), Primary/Active
   flags, warnings, bookability note
8. Edit drawer: pincode/city/zone/radius fields disabled with an explicit
   "add a new area to change this" note, matching the immutable-location
   rule
9. View Details drawer: Area Summary, Bookability Impact, Package Limit
   Impact, Recent Activity sections
10. Delete confirmation: area/pincode/status summary, bookability warning,
    last-active-area escalation warning
11. Set Primary confirmation modal (new this sprint — previously this was
    an un-confirmed instant PATCH call)

## Visual design notes

Consistent with the established pattern from the Business Profile redesign:
the app's default theme is light/neutral enterprise (`--surface`,
`--text-primary` custom properties), not a system-wide dark theme. The hero
card specifically uses a dark gradient treatment to match the reference
image's premium banner look, while KPI cards, the table, and sidebar cards
stay consistent with the rest of the light enterprise portal. This is a
deliberate, documented scope decision (same as the Business Profile sprint)
rather than a full dark-mode conversion, which would be a much larger,
separate design-system change.

## No longer a "basic table/modal" page

Old page: already had a hero + KPI + action-center structure, but it ran on
3 real bugs that undermined it in practice — clicking "Set Primary"
silently updated a field that didn't exist on the backend, the zipcode
validation panel called a nonexistent endpoint and fell back to a single
hardcoded pincode, and the plan limit was a bare frontend constant with no
backend source of truth. This sprint fixed all three with real backend
capability, added a working circular progress ring, restructured into the
ticket's two-column table+sidebar layout (Coverage Summary / Coverage
Rules / Recent Activity), and added a proper Set Primary confirmation flow.

## Real data, no fabrication

Every number shown (slots used, remaining slots, active area count, zone
tier, validation results) now comes from a real, live-verified backend
call. Fields the platform genuinely doesn't support (a full postal
database, PAN-style location certification) are handled with an honest,
documented heuristic (an 11-entry pincode-prefix table) rather than
fabricated data — see Remaining Blockers.
