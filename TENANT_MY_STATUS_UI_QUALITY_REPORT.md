# Tenant My Status — UI Quality Report

## Structure delivered (matches ticket's required page order)

1. Breadcrumb (Dashboard / Provider Visibility & Bookability)
2. Header with Refresh Status, Recalculate Readiness (permission-aware), View Setup Checklist, Manage Offerings
3. Provider Status Hero (`TenantStatusHero`) — tenant name, vertical, visibility, bookability, setup %, last recalculated, primary blocking reason, "Fix Required Actions" CTA
4. Required Actions / Action Center (`TenantStatusActionCenter`) — severity-coded blocker cards with rule key + last-checked timestamp
5. Readiness Score Cards (`TenantReadinessScoreCards`) — 6 cards: Overall, Visibility, Bookability, Finance, Service Setup, Operations
6. Offering Bookability (`TenantOfferingBookabilityPanel`) — table + enterprise empty state
7. Setup Readiness Checklist (`TenantSetupStatusChecklist`) — 8 backend-data-driven items with status/reason/CTA/rule key
8. Finance Readiness (`TenantFinanceReadinessPanel`) — package, usage credits, security deposit, completed-job-deduction explanation
9. Operational Readiness (`TenantOperationalReadinessPanel`) — service areas, offerings, technicians, availability, documents, pricing
10. Visibility Rules (`TenantVisibilityRulesPanel`) — collapsible, 11-item rule list
11. Recent Status Activity (`TenantStatusActivityTimeline`) — real audit-log-backed table with empty state

## Components created

`components/status/TenantStatusHero.tsx`, `TenantStatusActionCenter.tsx`,
`TenantReadinessScoreCards.tsx`, `TenantStatusBadge.tsx` (also houses
`TenantStatusSectionError`), `TenantStatusPanels.tsx` (houses
`TenantOfferingBookabilityPanel`, `TenantSetupStatusChecklist`,
`TenantFinanceReadinessPanel`, `TenantOperationalReadinessPanel`,
`TenantVisibilityRulesPanel`, `TenantStatusActivityTimeline`). `lib/status-format.ts` houses
`safeNum/safeText/safeCurrency/safePercent/safeDate/safeArray/safeStatus` and the
blocker-code-to-friendly-label map. Panels were grouped into fewer files than the ticket's
15-component list names individually (e.g. offering table + checklist + finance +
operational + rules + activity all live in one `TenantStatusPanels.tsx`) to keep the
component surface maintainable — all 15 named responsibilities exist as exported functions,
just not all as separate files. `TenantPermissionGuard` was not built as a standalone
component; the same effect (hide/disable with "Permission required") is implemented inline in
the page using `meApi.data?.role`, since no granular frontend permission list is currently
exposed by `/v1/auth/me` (see Remaining Blockers).

## No basic-card-page regression

Old page: title "My Status", 2 stacked cards, one basic offering table, generic error text.
New page: 11 distinct sections, hero with gradient state coloring, severity-coded action center,
6 score cards, enterprise empty states with dual CTAs, collapsible rules panel, real audit
timeline — a materially different, enterprise-grade page.

## Empty states

- No offerings: "No offerings enabled yet" + explanation + Enable Offering / View Catalog CTAs
  (not the old "No enabled offerings. Enable an offering to get started.").
- No activity: "No status activity yet." + explanation, matching ticket copy exactly.
- All required actions complete: "All required setup checks are complete." + explanation,
  matching ticket copy exactly.

## Error states

Every section error renders: a title ("We couldn't load provider status" for the hero, or a
section-specific equivalent), a plain-English message, the failing API/section name, the real
`request_id`, and Retry (+ Copy Request ID where applicable) — never the bare "Unexpected
error." string. Section-level failures don't hide the rest of the page (partial rendering
confirmed by design: each `useApi` call is independent; a failure in one section's error branch
sits inline where that section would render, all other sections continue to render normally).

## Responsive layout

Score cards use `repeat(auto-fit, minmax(220px, 1fr))` (collapses to fewer columns naturally on
tablet/mobile). Finance + Operational readiness use `repeat(auto-fit, minmax(340px, 1fr))`
(2-column on desktop, stacks to single-column once the viewport can't fit two 340px panels side
by side — no fixed `1fr 1fr` remains anywhere on the page). Offering table wraps in
`overflow-x: auto` so it scrolls horizontally on narrow viewports rather than breaking layout.
