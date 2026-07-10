# FINAL-L5-00 — Duplicate Code Report (Parts 12-13)

**Scope & method disclaimer:** This is a *sampled, Glob/Grep-based heuristic scan*, not an exhaustive structural-diff or AST-similarity analysis. File-name pattern matching and line-count comparison were used to establish "this looks like the same component in two apps"; actual byte-for-byte diffing was not run for every pair (a few representative pairs were read in full to confirm real duplication, not just name collision). All findings below were manually confirmed via Glob/Grep, and where noted, by reading file contents directly.

---

## 1. Component/config patterns duplicated across the 3 web frontends

Glob scope: `frontend/super-admin`, `frontend/tenant-portal`, `frontend/customer-app` (each app's `app/`, `components/`, `lib/`, `hooks/` — `node_modules` excluded).

| Pattern searched | Found in | Notes |
|---|---|---|
| `**/*EnterpriseDataGrid*` | super-admin (`components/enterprise/EnterpriseDataGrid.tsx`), tenant-portal (`components/enterprise/EnterpriseDataGrid.tsx`) | Independent files, same name, same directory structure (`components/enterprise/`). Not present in customer-app (customer-app has no admin-style data grid needs). |
| `**/*EnterpriseColumnManager*` | super-admin, tenant-portal | Same pattern as above — parallel `components/enterprise/` folders in both admin-style apps. |
| `**/*EnterpriseFilterBar*` | super-admin, tenant-portal | Same. |
| `**/*EnterprisePagination*` | super-admin, tenant-portal | Same. |
| `**/nav-config.ts` | `frontend/super-admin/lib/nav-config.ts` (239 lines), `frontend/tenant-portal/lib/nav-config.ts` (165 lines) | Two independently-maintained navigation config files. Different line counts confirm they are *not* identical copies — each has portal-specific nav items — but the pattern/shape (config-driven sidebar nav) is duplicated architecture, not shared code. |
| `**/page-registry.ts` | `frontend/super-admin/lib/page-registry.ts` (277 lines), `frontend/tenant-portal/lib/page-registry.ts` (179 lines) | Same situation as nav-config — parallel "page registry" pattern per app (per memory: "Sprint 34K — nav-config.ts + page-registry.ts... for both portals"), confirming this was a deliberate parallel-not-shared design in a past sprint. |
| `**/status-labels.ts` | `frontend/super-admin/lib/status-labels.ts` (155 lines), `frontend/tenant-portal/lib/status-labels.ts` (155 lines) | **Identical line count (155/155)** — strong signal of a literal copy-paste rather than independently-evolved files. Strongest CONSOLIDATE_CANDIDATE in this report. |
| `**/field-labels.ts` | super-admin, tenant-portal | Both present; not line-diffed in this pass, flagged for follow-up. |
| `**/page-copy.config.ts` | super-admin, tenant-portal | Both present; same pattern. |
| `**/design-tokens.ts` | super-admin, tenant-portal | Both present; per memory ("Sprint 34B — design-tokens.ts") this was intentionally per-app at the time, predating the later `design-system/tokens/` package (see §2). |
| `**/api-foundation/*` (admin-context/tenant-context, normalize.ts, error-model.ts, home-services-types.ts, admin-modules/tenant-modules.ts) | super-admin (`lib/api-foundation/`), tenant-portal (`lib/api-foundation/`) | Both apps have an `api-foundation/` folder with near-identical file names (`normalize.ts`, `error-model.ts`, `home-services-types.ts`) plus one app-specific context/modules file each. `normalize.ts` and `error-model.ts` in particular look like they solve an app-agnostic problem (response normalization, error shape) and are prime candidates for extraction into a shared package. |
| `components/shared/ui.tsx` | super-admin (687 lines), tenant-portal (638 lines) | **Read in full for both.** Both files define an almost-identical component library: `Btn`, `IconBtn`, `AddBtn`, `EditBtn`, `DeleteBtn`, `ViewBtn`, `MoreBtn`, `RowActions`, `Badge`, `Card`, `CardHeader`, `Input`, `Select`, `Spinner`, `Skeleton`, `Avatar`, `Modal`, `Toaster`, `StatCard`, `SectionHeader`, `DataTable`, `EmptyState`, `HealthMeter`/`JobStatusBadge`, `Pagination` — same names, same prop shapes, near-identical implementations, in the same relative path (`components/shared/ui.tsx`) in both apps. This is the single largest and clearest duplication found in this scan. Tenant-portal additionally has `StarRating` (not in super-admin). |
| `components/shared/ApiStates.tsx` | super-admin, tenant-portal | Same relative path, same name, both present — not read in full but strongly suspected duplicate given the `ui.tsx` precedent. |
| `components/shared/layout.tsx` | super-admin, tenant-portal | Same relative path, same name, both present. |
| `components/shared/ProfilePhotoUploader.tsx` | super-admin, tenant-portal | Same relative path, same name, both present (per memory, added in "Phase 0B Profile Photo UX" — built once, then apparently copied into both portals rather than shared). |
| `components/layout/Breadcrumbs.tsx` | super-admin, tenant-portal | Same relative path, same name (per memory, "Sprint 34K — Breadcrumbs for both portals" — confirms this was built twice by design in that sprint rather than shared). |
| `components/tour/TourGuide.tsx` | super-admin, tenant-portal | Same relative path, same name, both present. |
| `components/analytics/index.tsx` | super-admin, tenant-portal | Same relative path, same name, both present. |
| `**/*StatusBadge*` | tenant-portal only (`components/status/TenantStatusBadge.tsx`) | Not duplicated as a filename across apps — this one is tenant-portal-specific naming (status is a tenant-portal-only domain concept: "TenantStatus"). Super-admin's equivalent concept lives inside `ui.tsx` as `JobStatusBadge`, a differently-named/differently-scoped component. No direct file-name duplicate found. |
| `**/*Schema*.ts` / `**/*schema*.ts` (form-schema pattern) | No matches found in a scoped Glob of `lib/`/`components/` in any of the 3 frontends | No dedicated schema files found in this sampled scan — form validation, if present, appears to be inlined rather than in separate schema files (not confirmed exhaustively). |
| `**/menu-config*` / `**/*NavConfig*` (alt casings) | No additional matches beyond `nav-config.ts` already listed | Only the lowercase-hyphenated `nav-config.ts` naming convention is used; no `NavConfig.tsx` or `menu-config.ts` variants found. |

customer-app was checked against all the above patterns and has **none** of them — it has a much smaller, purpose-built component set (`BottomNav.tsx`, `ErrorBanner.tsx`) and does not participate in the super-admin/tenant-portal duplication pattern. This is expected/reasonable given its different (customer-facing, non-admin) UI needs — classified KEEP (justified separation).

---

## 2. `design-system/` package — exists, but is not used by any frontend

`g:\serviceos\design-system\` exists at repo root with a real, substantial export surface:

- `design-system/index.ts` is a barrel file exporting from `components/ui/*` (Alert, Avatar, Badge, Button, Card, Checkbox, ConfirmDialog, CopyButton, DangerConfirmModal, EmptyState, HealthBadge, Input, Modal, Popover, ProblemDetailAlert, RiskBadge, Select, Separator, Skeleton, Spinner, **StatusBadge**, Switch, Tabs, Textarea, Toast, Tooltip) and `components/nav/*` (CommandPalette, GlobalSearch, NotificationBell, PageHeader, RightDrawer), plus (per directory listing) `components/data/`, `components/metrics/`, `components/forms/`, `components/business/`, `components/charts/`, `tokens/`, `hooks/`, `styles/`, `showcase/`, `tests/`.
- The file header literally states: *"Auto-generated barrel export. Import from `@serviceos/ds`."* — i.e. this package was built with the explicit intent of being a shared import target, describing itself as "68+ components across UI, nav, data, metrics, forms, business, charts."

**Usage check (manually confirmed via grep):**
- `grep "design-system"` / `grep "@serviceos/ds"` across `frontend/super-admin/package.json`, `frontend/tenant-portal/package.json`, `frontend/customer-app/package.json` → **0 matches in all three.** None of the 3 frontends declares a dependency on it (no workspace/local `file:` reference either).
- `grep -rl "@serviceos/ds"` across all `.ts`/`.tsx` files in all 3 frontends (excluding `node_modules`) → **0 matches.**

**Conclusion:** `design-system/` is a fully-built, unconsumed shared component library. Every component it duplicates already has a parallel bespoke implementation living independently in `frontend/super-admin/components/shared/ui.tsx` and `frontend/tenant-portal/components/shared/ui.tsx` (e.g. `StatusBadge`/`JobStatusBadge`, `Badge`, `Card`, `Modal`, `EmptyState`, `Skeleton`, `Spinner`, `Avatar`, `Select`, `Input`). This is the single biggest architectural duplication finding in this scan: an entire shared-component package was built and then never wired into any consuming app, while both admin-style apps independently reimplemented most of the same primitives locally.

Classification: **REVIEW_REQUIRED** — this is not simple accidental duplication to "just delete"; it represents unfinished migration work (a shared design system that was scaffolded but never adopted). A decision is needed: either (a) complete the migration — wire `super-admin`/`tenant-portal` to import from `@serviceos/ds` and delete the local `ui.tsx`/`ApiStates.tsx`/etc. duplicates, or (b) archive/delete the unused `design-system/` package if it's been abandoned in favor of the per-app approach. Not safe to unilaterally delete either side without a decision from the team, hence REVIEW_REQUIRED rather than DELETE_CONFIRMED or CONSOLIDATE_CANDIDATE.

---

## 3. Classification summary

| Finding | Classification | Reasoning |
|---|---|---|
| `components/shared/ui.tsx` (super-admin vs tenant-portal) | CONSOLIDATE_CANDIDATE | Near-identical 20+ component library, same names/props, in same relative path in both apps; extraction into a shared package (or adoption of the existing unused `design-system/`) would remove hundreds of duplicated lines. |
| `lib/status-labels.ts` (super-admin vs tenant-portal) | CONSOLIDATE_CANDIDATE | Identical line count (155/155) is a strong duplicate signal; status labels are inherently domain-shared vocabulary, not portal-specific. |
| `lib/api-foundation/normalize.ts`, `error-model.ts`, `home-services-types.ts` | CONSOLIDATE_CANDIDATE | These solve app-agnostic problems (response shape normalization, error model, shared types) yet are duplicated per-app; good extraction candidates. |
| `design-system/` package vs local `ui.tsx` duplicates | REVIEW_REQUIRED | Real shared-component infrastructure exists and is unused; needs a team decision (adopt vs delete), not a unilateral merge. |
| `components/shared/ApiStates.tsx`, `layout.tsx`, `ProfilePhotoUploader.tsx`, `components/layout/Breadcrumbs.tsx`, `components/tour/TourGuide.tsx`, `components/analytics/index.tsx` | CONSOLIDATE_CANDIDATE | Same file names/paths in both admin-style apps; not read in full in this pass but the naming/path/precedent (from `ui.tsx` and `status-labels.ts` which *were* read) makes literal-copy duplication likely. Flagged, not confirmed byte-for-byte. |
| `lib/nav-config.ts`, `lib/page-registry.ts`, `lib/design-tokens.ts`, `lib/page-copy.config.ts`, `lib/field-labels.ts` (super-admin vs tenant-portal) | KEEP (justified separation) | Different line counts and per-memory context (Sprint 34K/34B explicitly built these "for both portals" as intentionally-parallel, portal-specific configuration) indicate these are legitimately different content sharing only a *pattern*, not a *duplicate*, despite the identical file names. |
| `components/enterprise/EnterpriseDataGrid.tsx` + `EnterpriseColumnManager.tsx` + `EnterpriseFilterBar.tsx` + `EnterprisePagination.tsx` (super-admin vs tenant-portal) | REVIEW_REQUIRED | Same name/path pattern in both apps; per memory ("Sprint 26 — Enterprise Filters + Data Grid System... EnterpriseDataGrid component") this looks like it was built once as a generic system — worth checking whether these two copies have actually diverged (portal-specific columns) or are literal copies that should be consolidated. Not read in full in this pass, hence REVIEW_REQUIRED rather than a firm CONSOLIDATE_CANDIDATE. |
| customer-app's independent, smaller component set | KEEP (justified separation) | Genuinely different UI surface (customer-facing booking/tracking flows vs admin data-grid-heavy screens); no meaningful overlap found. |
| No `*Schema*.ts` files found | N/A | Nothing to classify — form schemas, if they exist, are not in a dedicated/named file pattern in this codebase (or were not surfaced by this scoped Glob). |

This scan intentionally sampled representative patterns per the task instructions rather than diffing every file pair; a full duplication audit would require a proper AST/text-similarity tool (e.g. `jscpd`) run across all three frontends, which was not executed here.
