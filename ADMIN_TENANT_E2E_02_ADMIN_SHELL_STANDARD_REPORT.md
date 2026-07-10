# Admin Shell Design Standard Report (Part 2)

## Target standard (spec)
Left sidebar, top header, breadcrumb, page title, page subtitle, primary action area,
notification icon, user/profile menu, main content container, loading/empty/error state support.

## What AdminLayout.tsx actually provides today
- Left sidebar: yes — collapsible (68px/248px), grouped, icons+labels, per-vertical dynamic
  sub-sections driven by `verticalCatalogApi.getEffectiveMenu()`.
- Top header: yes — search box (visual only, not wired to a real search endpoint — same as
  prior sprint's finding, unchanged), "All Systems Live" status pill (static, not backed by
  `/health`), theme toggle, notification bell (see Part 10), user name+avatar+role label, logout.
- Breadcrumb: NOT provided by AdminLayout itself. `components/layout/Breadcrumbs.tsx` exists as
  a separate component; some but not all pages import and render it themselves inside their own
  content area rather than the shell rendering it universally.
- Page title/subtitle: not part of the shell — each page renders its own `<h1>`/subtitle inline;
  consistent in practice (spot-checked in Part 4) but not enforced by a shared component.
- Primary action area: not part of the shell; each page places its own CTA button(s).
- Main content container: yes — `<main>` with `maxWidth:1440, margin:auto` centered container.
- Loading/empty/error states: not part of the shell; each page uses `ApiStates.tsx` components
  individually (see Part 8).

## Sidebar grouping: real vs spec's illustrative target
Spec's illustrative groups (Dashboard/Home Services/Tenants/Operations/Finance/Notifications/
Audit/Reports/Settings) are close to, but not identical to, the REAL rendered `NAV_GROUPS` in
`AdminLayout.tsx`: Overview, Providers, Operations, Catalog, Pricing & Rules, Home Services,
Finance, Marketing & Growth, Platform. This is already a sensible, deliberate grouping (per
inline comments explaining provider lifecycle ordering and Home-Services-only scoping) — no
forced rename was done. The real gap is not naming, it's the **10 orphaned real routes** with no
sidebar entry at all (see Part 1): real-estate, coaching, bookability, reports, ai, ai-chat,
service-invoices, provider-wallets, commission-records, payments, financial-events. Recommended
follow-up (not done in this sprint per Part-3-only-fixes-shell-if-blocking scope): either add
these to `NAV_GROUPS` or confirm they are intentionally reachable only via deep-links from other
pages.

## Two competing nav configs (real bug, fixed in Part 3)
`lib/nav-config.ts`'s `ADMIN_NAV_GROUPS` was a second, independently maintained sidebar
definition, used only for active-id resolution, not rendering. It had drifted from the real
sidebar and used a coarse per-path-segment map, causing sub-routes like `/admin/users/roles` to
report the parent's nav id instead of their own. Fixed in Part 3 by deriving active-id directly
from the real, rendered `NAV_GROUPS` (single source of truth) via longest-href-prefix match.
`nav-config.ts` itself was left in place (still imported nowhere now except by nothing) — not
deleted, to stay within "small safe fixes" scope; flagged as dead/stale code for cleanup later.
