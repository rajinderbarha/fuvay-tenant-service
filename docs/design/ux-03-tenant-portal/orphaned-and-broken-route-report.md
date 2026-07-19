# Orphaned / Broken-Nav Route Report

Method: cross-referenced every `app/(tenant)/**/page.tsx` route against
`frontend/tenant-portal/lib/nav-config.ts` (`TENANT_NAV_GROUPS`,
`TENANT_PATH_TO_NAV_ID`, `TENANT_PROVIDER_PATH_TO_NAV_ID`). This is a
naming/config cross-reference, not a per-file manual click-through of the
running app (blocked — see execution-mode.md).

## Routes with no corresponding nav-config entry (orphaned from primary nav)

`/ai-chat`, `/media`, `/inventory`, `/packages`, `/provider/complaints` (+detail),
`/provider/customer-price-preview`, `/provider/offerings`, `/provider/pricing`,
`/provider/refund-requests`, `/provider/reviews` (+ sub-routes),
`/provider/rework-requests`, `/provider/service-invoices`,
`/provider/service-options`, `/provider/service-setup`, `/provider/services`,
`/provider/subscription-status`, `/provider/team-members`, `/provider/wallet`,
`/service-areas`, `/setup/checklist`, `/setup/service-coverage`, `/staff`,
`/staff/[id]`, `/tenant/setup/availability`, `/tenant/setup/services`,
`/users`, `/wallet`.

These are reachable only by direct URL or from within another page's local
links — they don't appear in `TENANT_NAV_GROUPS`. Some are clearly meant to be
reached through the `/provider/*` conventions actually used by
`TENANT_PROVIDER_PATH_TO_NAV_ID` (a second, narrower alias table for
`/provider/*` sub-paths); others (`/staff`, `/users`, `/wallet`,
`/setup/checklist`) have no alias anywhere and are the strongest orphan
candidates.

## Confirmed duplicate targets (not orphaned, but nav points two ways)

`resolveTenantNavId()` already merges several of these onto shared nav ids
(e.g. `jobs` and `service-jobs` both resolve to `"jobs"`; `catalog`,
`inventory`, and `media` all resolve to `"provider-services"`). This is
consistent with `tenant-route-duplication-map.csv` above but means the nav
highlight is currently ambiguous about which underlying page is "the" catalog
page.

## Not assessed

Actual runtime 404s/broken links (would require the dev server + browser,
blocked in Mode B) and deep-linked sub-navigation inside pages (e.g. anchor
links like `#quote` used by this phase's dev showcase are new proposals, not
verified against production page internals).
