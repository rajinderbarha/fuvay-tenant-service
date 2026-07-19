# UX-01 Source Compatibility Report

Classification is by static source reading only (MODE B — see execution-mode.md); nothing below
was verified by running tsc/build.

| Item | Classification | Notes |
|---|---|---|
| design-system tokens/ThemeProvider | Reusable-as-is | Used directly via `@serviceos/design-system` import in all UX-02 components. |
| PageShell / PageHeader / Section | Reusable-as-is | Used unchanged in every UX-02 page/pattern. |
| DataTable | Reusable-as-is | Used as the table engine inside `EnterpriseListPage`. |
| StatusBadge | Reusable-with-extension | Reused for tenant status, risk, security-observation status. Any new status strings (e.g. `product_policy_blocked`) must be added to its existing status-color mapping, not a second color system — flagged in `design-governance-rules.md`. |
| Button, Card, Modal, Drawer, Tooltip, Toast/Alert/Banner, Skeleton/Spinner, EmptyState/ErrorState/PermissionDeniedState, Input/Textarea/Select | Reusable-as-is | No prop changes needed for UX-02 scope. |
| `lib/nav-config.ts` (`ADMIN_NAV_GROUPS`) | Reusable-with-extension | `lib/ux02/nav-ia.ts` extends the same `NavItem`/`NavGroup` shape (`Ux02NavItem`/`Ux02NavGroup`) rather than replacing it. Not wired into production `layout.tsx` — swapping production nav is a product decision (see `product-decisions-required.md`). |
| `lib/permission-catalog.ts`, `hooks/usePermissions.ts`, `PermissionGate.tsx` | Reusable-as-is | Existing gating pattern followed for any UX-02 code that touches production routes (`AdminLayout.tsx`, tenant/users pages); dev showcase routes deliberately do not add new gates since they are non-production. |
| `components/enterprise/*` (pre-existing enterprise grid/filter/pagination) | Incomplete | Pre-dates the design-system tokens; does not use `@serviceos/design-system` primitives. Not replaced (out of scope to touch 227 files across the app), but the new `components/ux02/patterns/EnterpriseListPage.tsx` is the design-system-native replacement pattern going forward for anything built under this phase. |
| Existing ~150 `app/admin/**` routes | Mixed | See `existing-super-admin-route-audit.csv` for per-route classification; none deleted. |

## Design-system fixes made under this phase
None required. No prop signature gaps were found for the UX-02 component set (list/detail/review
patterns, dashboard, status tags) against the existing design-system exports.
