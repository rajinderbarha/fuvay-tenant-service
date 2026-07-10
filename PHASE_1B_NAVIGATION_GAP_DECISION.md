# Phase 1B — Navigation Editor Gap Decision

## Decision: **Option B — Defer**

The dedicated `/admin/navigation` editor page is **not implemented this
sprint**, per the ticket's own Option B criteria — all 5 conditions are met:

1. **Effective menu API is fully working.** `GET
   /v1/admin/catalog/navigation/effective-menu` live-verified 200,
   returns real permission- and vertical-aware menu data, confirmed across
   Phase 0, Phase 1, and this sprint.
2. **Sidebar is duplicate-free.** Static-verified repeatedly (`Pricing
   Tiers`/`City-Zip Mapping`/`Pricing Rules` each appear exactly once, no
   global `Brands`/`Brand Requests`) — unchanged and re-confirmed this
   sprint.
3. **Navigation config is seeded idempotently.** The sidebar structure
   (`AdminLayout.tsx::NAV_GROUPS`) is static code, not DB-seeded data — there
   is nothing to seed or re-seed; it's inherently idempotent by construction.
4. **Missing editor is documented as non-blocking for Phase 1.** This
   document is that record.
5. **Future phase/backlog ticket is created.** See below.

## Rationale

The ticket's assumed backend endpoints (`GET /v1/admin/navigation`, `PUT
/v1/admin/navigation/{item_id}`, `POST /v1/admin/navigation/rebuild`, `POST
/v1/admin/navigation/validate`) were confirmed **not to exist** (all 404,
live-verified this sprint). Building a full navigation-governance CRUD
system — with a tree-view editor, per-item permission/engine/vertical
requirement management, and rebuild/validate actions — is a substantial new
feature, not a "close the gap" fix. The current architecture (static
`NAV_GROUPS` in code + dynamic `effectiveMenu`-driven visibility) already
achieves every *functional* requirement the ticket cares about: a clean,
duplicate-free, permission-and-vertical-aware sidebar. There is no evidence
of a real defect — only a missing administrative convenience UI for
something that currently requires a code change to modify.

## Backlog ticket (for a future sprint)

**Title**: Navigation Governance Admin Editor
**Scope**: `/admin/navigation` page with summary cards (Total Menu
Items, Active Items, Hidden By Permission, Hidden By Vertical, Duplicate
Issues), tree view, and `GET/PUT /v1/admin/navigation`,
`POST /v1/admin/navigation/validate` endpoints backed by a new
`navigation_items` DB table (migrating the current static `NAV_GROUPS` array
into seed data) so nav structure becomes admin-editable without a
deployment.
**Not scoped for Phase 1B or Phase 2** (catalog/pricing) — should be
picked up as its own dedicated sprint given the schema migration involved.
