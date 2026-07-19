# Tenant Design Debt Inventory

- 4 duplicate service-area routes, 3 duplicate catalog routes, 2 duplicate
  job-list routes (see tenant-route-duplication-map.csv) — inconsistent
  information scent for the same underlying concept.
- `/wallet` naming risk (implies payout capability the platform doesn't
  offer) — see product-decisions-required.md.
- No single centralized profile-completion/review-state component existed
  before this phase; each page likely re-implemented its own status text
  (not independently confirmed per-file this phase — inferred from the
  absence of a shared component in `lib/`/`components/` prior to
  `ReviewStateBanner.tsx`).
- Nav-config's alias tables (`TENANT_PATH_TO_NAV_ID`,
  `TENANT_PROVIDER_PATH_TO_NAV_ID`) already show signs of the same
  consolidation need UX-03's IA proposes.
