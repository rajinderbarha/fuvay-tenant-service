# FINAL-L5-04 — Navigation Security Report

## Core rule under test: "no security-by-frontend-hiding-only"
For every route category re-verified this sprint (see Direct Route Guard Report and Permission Navigation Matrix, both produced this sprint from real live API calls, not assumptions), hiding a sidebar item is **not** the sole protection — the underlying API independently enforces auth (401 unauthenticated), role (403 wrong role), and tenant-scope (403 cross-tenant) regardless of what the frontend renders. This was re-confirmed, not newly built, this sprint.

## Real findings by rule
| Rule | Status |
|---|---|
| Hidden routes must still be backend-guarded | **Confirmed** for auth/role/tenant-scope dimensions (401/403 real, tested). **Not enforced** for tenant-entitlement (module/category) dimension — see below. |
| No cross-tenant route exposure | **Confirmed** — `/v1/provider/usage-credits/balance` returns 403 for a customer with no tenant membership; established RBAC test suite (21/21, FINAL-L5-01B) unaffected by this sprint's changes (no auth code touched). |
| No runtime mock configuration | **Confirmed** — `verticalCatalogApi.getEffectiveMenu()` is a real network call against a real backend endpoint (`app/engines/vertical_catalog/service.py`), no mock/stub found in the navigation data path. |
| Permission labels never shown raw | **Confirmed** — sidebar/breadcrumb labels come from curated `NavItem.label`/`page-registry.ts` strings, never raw permission keys (re-checked this sprint while wiring breadcrumbs). |

## The one real gap: tenant entitlement is not enforced anywhere, frontend or backend, for navigation purposes
This is the honest, load-bearing finding of this entire sprint (fully detailed in `FINAL_L5_04_TENANT_ENTITLEMENT_NAVIGATION_REPORT.md`): `tenant.category_id` is always NULL for every seeded tenant, so `enabled_engines`/`modules` resolution — the mechanism that *would* drive both a hidden sidebar item and a backend-side entitlement check — never has real data to filter on. The practical effect is **every tenant-portal nav item is shown to every tenant, and every corresponding backend route is reachable by any authenticated tenant user**, regardless of which modules/verticals that tenant is actually supposed to have access to.

This is **not** a case of "security-by-hiding-only" (a specific, narrower anti-pattern where the frontend hides something the backend would allow) — it is a broader case of the entitlement dimension not existing as an enforced concept at all, on either side. It is documented plainly rather than mischaracterized as the narrower rule violation, and is the central reason `PARTIAL_READY_WITH_FINAL_L5_04_BLOCKERS` (not a clean READY) is this sprint's honest recommendation.

## What this sprint did NOT introduce or regress
Neither of this sprint's two real code changes (menu live-refresh via context, breadcrumb wiring) touches any auth/permission/guard code path — both are purely presentational (sidebar section visibility, breadcrumb text). No new attack surface was created; `tsc`/build/existing RBAC test suite all remain green.

## Result
No new security regression introduced this sprint. One pre-existing, structural gap (tenant entitlement not enforced anywhere) re-confirmed and clearly documented as the central blocker, consistent with prior reports in this sprint.
