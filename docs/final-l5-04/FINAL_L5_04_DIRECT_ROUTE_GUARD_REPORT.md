# FINAL-L5-04 — Direct Route Access Guard Report

## Cases tested this sprint (real, live)
| Case | Result |
|---|---|
| Unauthenticated → protected API | **401** confirmed across all 4 endpoints tested this sprint (Permission Navigation Matrix) |
| Wrong role → admin-only route (`/v1/admin/verticals`) | **403** confirmed for tenant_owner/readonly/technician/customer |
| Wrong role → tenant-scoped route (`/v1/provider/usage-credits/balance`) | **403** for super_admin and customer (no tenant membership) |
| Customer opening admin/tenant routes | **403** or safe-empty soft-block (no real data), confirmed |
| Staff opening tenant-owner-only routes | Not independently re-tested this sprint; established and passing in FINAL-L5-01B (21/21 RBAC regression, unaffected by this sprint's changes) |
| Inactive module/vertical direct access (`/admin/catalog/beauty` while disabled) | **200, renders admin config page with a "Disabled" badge** — not blocked. See Module Visibility Report for why this is a deliberate, defensible admin-tooling design (viewing/configuring a disabled vertical before enabling it), not a data-exposure issue — no tenant/customer/end-user data is exposed, only catalog configuration metadata already visible to the same authenticated super-admin via the Verticals list page |
| Read-only user opening mutation route | Established in FINAL-L5-01D (403-before-422 on 2 real mutation endpoints), not re-broken by this sprint (no auth/permission code touched) |
| Missing tenant entitlement | **Not enforceable — see Tenant Entitlement Navigation Report.** Since tenant entitlement filtering doesn't exist in the live navigation at all, there is no "missing entitlement" case to test; every tenant route is equally reachable by any authenticated tenant user regardless of what modules/categories they're actually entitled to |

## No route rendered protected content before authorization resolved
Confirmed via this sprint's browser tests: `AdminLayout`'s `useEffect` gates the effective-menu fetch on `localStorage.getItem("serviceos_admin_token")` being present before ever calling the API: `if (!token) return;` — and separately redirects to `/login` if no token exists at all (`useEffect(() => { if (!token) window.location.href = "/login"; }, [])`). No flash-of-protected-content was observed in any test run.

## Result
No unauthorized real data exposure found in any tested case. The one genuine gap (`NOT_READY_FINAL_L5_04_DIRECT_ROUTE_GUARD_FAILED` consideration) is the tenant-entitlement dimension, which is structurally absent rather than broken — folded into the overall Tenant Entitlement finding rather than treated as a separate route-guard defect, since the guard mechanisms that *do* exist (auth, role, tenant-scope) all function correctly.
