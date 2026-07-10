# Remaining Blockers / Gaps (ADMIN-TENANT-E2E-02)

None of the below block certification of the admin shell/nav/enterprise-UI-baseline scope of this
sprint; all are documented follow-ups for future, more targeted sprints.

1. **Orphaned real routes with no sidebar entry** (Part 1/2): `/admin/real-estate/*`,
   `/admin/coaching/*`, `/admin/bookability/*`, `/admin/reports`, `/admin/ai/*`, `/admin/ai-chat`,
   `/admin/service-invoices`, `/admin/provider-wallets`, `/admin/commission-records`,
   `/admin/payments`, `/admin/financial-events` exist and build/render correctly but have no
   sidebar link in the rendered `NAV_GROUPS`. `lib/nav-config.ts`'s separate, unused
   `ADMIN_NAV_GROUPS` DOES list several of these — it's now confirmed dead code (no imports left
   after Part 3's fix) but was clearly meant to be the eventual real sidebar. Recommend either
   reconciling the two, or deleting `nav-config.ts` and adding the missing items to
   `AdminLayout.tsx`'s `NAV_GROUPS` directly.
2. **No breadcrumb rendered anywhere** (Part 4/8): `Breadcrumbs.tsx` exists, zero admin pages use
   it. Retrofitting 157 page files is out of this sprint's scope.
3. **Notification bell has no onClick** (Part 10): purely decorative; recommended minimal fix is
   a one-line `onClick` to navigate to `/admin/notifications`.
4. **No explicit "session expired" state** (Part 9): an invalid/corrupted token silently bounces
   to `/login` rather than showing a message; the presence-only token check doesn't validate the
   JWT, and API 401s inside `getEffectiveMenu()` are swallowed.
5. **Topbar role label is hardcoded "Platform"** (Part 4/9), not the user's real role.
6. **7 pages use direct `fetch()` instead of `lib/api.ts`** (Part 12): all verified working
   against the real backend with real tokens — a consistency/architecture item, not a runtime bug.
7. **EmptyState/ApiEmptyState duplication** (Part 8): two near-identical components; a rename/
   alias cleanup, not urgent.
8. **`lib/mock.ts` still dead code** (Part 12), unreferenced but not deleted.
9. **Search box and "All Systems Live" status pill are decorative** (Part 4): not wired to a real
   search API or `/health` endpoint respectively — pre-existing, not fabricated as new features.
10. Carried in from prior sprint (`ADMIN_TENANT_E2E_01_REMAINING_BLOCKERS.md`), tenant-side, out
    of this admin-only sprint's scope: provider business-profile RBAC gap, no tenant read-only UI
    mode, legacy `/provider/wallet` naming — re-verified none of these leak into any admin page.
11. `npm run lint` still has no working config — pre-existing, explicitly non-blocking per spec.

No P0/blocking issue was found in the admin shell, navigation, active-state, auth/session, or
enterprise-UI-baseline surfaces tested. TypeScript, build, and all 26 new Playwright tests pass.
