# ADMIN-TENANT-E2E-09 — Tenant Service Setup Routes Report

## Real routes confirmed (verified via file system + nav-config.ts + live browser)

| Route | File | Status |
|---|---|---|
| `/tenant/setup/services` | `app/(tenant)/tenant/setup/services/page.tsx` | REAL, live wizard (Service Setup), linked from sidebar as "Service Setup" |
| `/provider/service-coverage` | `app/(tenant)/provider/service-coverage/page.tsx` | REAL, live page (Service Coverage), linked from sidebar as "Service Coverage" |
| `/setup/service-coverage` | `app/(tenant)/setup/service-coverage/page.tsx` | **LEGACY REDIRECT STUB** — file body is exactly `redirect("/provider/service-coverage")`, nothing else. Confirmed via browser: navigating here 302s to `/provider/service-coverage` (final URL matches, body identical, len=3435 vs 3429). Not linked from nav-config.ts. |
| `/setup/checklist` | (per prior sprint) | Redirects to `/onboarding-status` (not re-verified this sprint, out of primary scope, consistent with E2E-08 notes) |
| `/onboarding-status` | `app/(tenant)/onboarding-status/page.tsx` | REAL, live, mapped in nav-config as `provider-status` |
| `/dashboard` | `app/(tenant)/dashboard/page.tsx` | REAL, live, tenant name confirmed |

nav-config.ts source of truth (`frontend/tenant-portal/lib/nav-config.ts`):
```
{ id: "provider-services",         label: "Service Setup",    href: "/tenant/setup/services" }
{ id: "provider-service-coverage", label: "Service Coverage", href: "/provider/service-coverage" }
```
`/setup/service-coverage` is NOT in nav-config — it is dead/legacy, kept only as a redirect for old bookmarks/links.

## Browser verification (Playwright, `E2E_APP=tenant`, real Chrome, real login as `provider@serviceos.in`)

Route smoke test (`e2e/tenant-service-setup-e2e09.spec.ts`) — final clean run, all passed:
```
/dashboard -> http://localhost:3001/dashboard | status=200
/tenant/setup/services -> http://localhost:3001/tenant/setup/services | status=200
/provider/service-coverage -> http://localhost:3001/provider/service-coverage | status=200
/setup/service-coverage -> http://localhost:3001/provider/service-coverage | status=200 (redirected, confirmed)
/onboarding-status -> http://localhost:3001/onboarding-status | status=200
```
- Tenant shell (TenantLayout) appears on all routes.
- "Demo AC Services" (real business_name from DB) appears on dashboard — confirmed, not a placeholder like "Your Business".
- No NaN/undefined found in body text (assertions passed).
- No forbidden financial/bargain labels found.
- No raw JSON/debug UI observed in manual page reads.
- A single transient 404 was observed on one retry of `/tenant/setup/services` mid-run; a clean isolated re-run immediately after returned 200 consistently — attributed to Next.js dev-server cold-route-compile timing (first hit after server (re)start), not a real routing bug. Documented for transparency.

## Verdict: PASS
