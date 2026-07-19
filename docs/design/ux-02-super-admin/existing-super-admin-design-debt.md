# Existing Super Admin Design Debt

Derived from `existing-super-admin-route-audit.csv` and `super-admin-duplication-map.csv`.

## Duplication clusters (candidates for MERGE)
- `brand-requests` / `brands` / `service-setup/brands` — three overlapping brand-management
  surfaces.
- `checklist-templates` / `checklists` — overlapping checklist admin.
- `catalog` / `catalog-module` — possible duplicate catalog surface.
- `pricing-rules` (top-level) / `pricing/*` subtree — legacy top-level page likely superseded by
  the newer `pricing/` group.
- Multiple finance list pages (`payments`, `financial-events`, `service-invoices`,
  `provider-wallets`, `commission-records`) that a prior phase's disposition matrix already flags
  for eventual tab-consolidation into one Finance Hub (see `product-decisions-required.md`).

## Structural debt
- No consistent nav grouping discipline — some pages sit in a generic `reports`/`core` bucket that
  doesn't match their actual domain (analytics, account settings).
- Several pages exist with zero sidebar entry today (see the `AdminLayout.tsx` fix in this phase
  for 6 of them — Provider Bookability + 5 Finance pages); more may exist that weren't restored in
  this phase since it was frontend-only and scoped to what was flagged in the audit.
- Pre-UX-02 `components/enterprise/*` toolkit (grid/filter/pagination) doesn't use
  `@serviceos/design-system` tokens/components — visually and structurally inconsistent with the
  new `EnterpriseListPage` pattern this phase introduces.

## Full detail
See `existing-super-admin-route-audit.csv` (per-area classification: KEEP_AND_REDESIGN / MERGE /
SPLIT / MOVE / DEPRECATE / DEVELOPMENT_ONLY / API_CONTRACT_REQUIRED / PRODUCT_DECISION_REQUIRED)
and `super-admin-duplication-map.csv` for the specific duplicate-route pairs.
