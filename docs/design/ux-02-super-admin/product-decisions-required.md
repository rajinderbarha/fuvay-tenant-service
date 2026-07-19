# Product Decisions Required

1. **Swap production nav to `UX02_NAV_GROUPS`?** `lib/nav-config.ts`'s `ADMIN_NAV_GROUPS` is still
   what `AdminLayout.tsx` renders. The new `Ux02NavItem`/`Ux02NavGroup` shape in `lib/ux02/nav-ia.ts`
   is a redesign proposal, not wired in. Deciding to cut over is a product/rollout decision (staged
   rollout? role-gated preview? all at once?).
2. **Saved views**: should saved-view persistence become a real backend-backed feature, and if so,
   per-user or per-tenant-admin-role?
3. **Global search**: is a unified cross-domain search endpoint worth building, and what's in scope
   (tenants only? + compliance + audit + settings)?
4. **Platform Configuration write path**: which settings actually get a real write endpoint with
   change history, versus staying informational/read-only indefinitely?
5. **Finance Hub tab consolidation**: `docs/.../final-page-disposition-matrix.csv` (referenced in
   `AdminLayout.tsx`'s inline comments from a prior phase) calls for 5 restored Finance sidebar
   pages (Service Invoices, Provider Wallets, Commission Records, Payments, Financial Events) to
   eventually become tabs of one consolidated Finance Hub workspace. That consolidation is
   explicitly out of scope for this phase and needs a product decision on priority/design.
6. **Enterprise list toolkit consolidation**: keep the pre-existing `components/enterprise/*`
   (EnterpriseDataGrid/FilterBar/etc.) and the new design-system-native `EnterpriseListPage`
   side by side long-term, or migrate the older toolkit's consumers onto the new pattern?
7. **i18n adoption**: whether/when to adopt an i18n framework platform-wide (see
   `localization-readiness-report.md`) — no framework exists today.
