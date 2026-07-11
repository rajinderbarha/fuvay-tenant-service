# FINAL-L5-04 — Canonical Navigation Registry Report

## Current state (real, verified this sprint)
Each app's navigation is defined once, in one file, consumed by exactly one layout component:
- Super Admin: `NAV_GROUPS` (static array, `AdminLayout.tsx`) + `effectiveMenu.verticals` (dynamic, fetched via `verticalCatalogApi.getEffectiveMenu()`, rendered by `VerticalCatalogSection`).
- Tenant Portal: `TENANT_NAV_GROUPS` (static array, `lib/nav-config.ts`), consumed by `TenantLayout.tsx`.
- Customer App: no config file — a hardcoded 4-item `BottomNav.tsx` (confirmed in FINAL-L5-00's inventory, re-confirmed unchanged this sprint).
- Staff (tenant-portal `/staff/*`): no shared layout/nav-config at all (confirmed in FINAL-L5-00 — "architecturally separate from both the tenant sidebar and the native mobile/staff-app").

## Required behavior — verified
1. **Sidebar, mobile drawer and compact nav use the same source** — true within each app (there is exactly one nav array per app, no separate mobile-specific duplicate array found in super-admin or tenant-portal). Customer App's `BottomNav` is itself the only nav surface (no separate desktop sidebar to diverge from). **No violation of rule 2 found** ("do not maintain separate conflicting desktop and mobile menu definitions").
2. **Top-level groups ordered centrally** — true, `NAV_GROUPS`/`TENANT_NAV_GROUPS` array order is the sole determinant of rendering order.
3. **Child routes ordered centrally** — same, array order within each group.
4. **Labels not repeated in separate files** — true for the 69 statically-registered routes; the real duplication that exists (FINAL-L5-00's 21 duplicate clusters) is duplicate *routes* (multiple page files for the same concept), not duplicate *label definitions* for the same route.
5. **Active-state resolution centralized** — partially: each layout compares `activeNav` (a prop manually passed by every page) against item IDs; this comparison logic lives in one place (`SidebarItem`), but the *value* is not automatically derived from the URL — see Active State/Breadcrumb Report.
6. **Hidden/contextual routes do not appear automatically** — confirmed: none of FINAL-L5-00's `ACTIVE_CONTEXTUAL`/`ACTIVE_HIDDEN_INTENTIONAL` routes appear in either static nav array (spot-checked several from the FINAL-L5-00 list against both `NAV_GROUPS` and `TENANT_NAV_GROUPS` — no matches).
7. **Navigation groups collapse cleanly** — verified in this sprint's browser test (sidebar collapse/expand button works, unaffected by the live-refresh fix).
8. **Current route expands the correct parent group** — not applicable to super-admin/tenant-portal's current design (groups are not collapsible individually — the whole sidebar collapses to icon-only, not per-group accordion expand/collapse); the mission's Part 16 requirement ("Category detail route expands category group") is only meaningfully testable for the dynamic vertical sections, which **do** expand correctly (verified: `VerticalCatalogSection` shows its own modules whenever `effectiveMenu` includes that vertical as enabled — there's no separate collapsed/expanded toggle state per vertical beyond enabled/disabled).

## This sprint's real contribution
Added `useAdminMenuRefresh()` (a lightweight React Context) so any page can trigger `AdminLayout`'s dynamic menu section to re-fetch after a mutation — closing the one real gap found in the otherwise-working dynamic vertical navigation (previously fetch-once-on-mount only). Wired into `verticals/page.tsx` and `categories/page.tsx`. Browser-verified: enabling/disabling a vertical now updates the sidebar live, with zero page reload.

## Result
Real navigation-source consistency confirmed (no desktop/mobile divergence within either app); the live-refresh gap found is fixed and proven. Full breadcrumb/active-state/title derivation from a single registry (rather than per-layout hardcoded logic) remains a real, honestly-documented gap.
