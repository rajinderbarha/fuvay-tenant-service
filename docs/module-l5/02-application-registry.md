# MODULE-L5-00 — Application Registry

| App ID | Name | Tech | Path | Start cmd | Auth | Roles | Route root | API base | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `super_admin` | Super Admin Console | Next.js (Turbopack) | `frontend/super-admin` | `npm run dev` (port 3000) | JWT via `/v1/auth/login`, `/v1/auth/me` | `super_admin`, `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly` | `/admin/*` | `http://localhost:8000/v1` | **ACTIVE** | 163 routes; subject of the entire FINAL-L5-05 chain (13 sprints, 46 docs) |
| `tenant_portal` | Tenant / Business Dashboard | Next.js | `frontend/tenant-portal` | `npm run dev` (port 3001) | Same JWT auth | `tenant_owner`, `staff` (in tenant-scoped views) | `/` (tenant-scoped) | same | **ACTIVE, PARTIALLY CERTIFIED** | 104 routes; certified separately by the `PHASE_6B_TENANT_*`/`TENANT_*` document set (23 files), never reconciled against FINAL-L5-05's methodology until this sprint |
| `customer_app_web` | Customer Web App | Next.js | `frontend/customer-app` | `npm run dev` (port 3002) | Same JWT auth | `customer`, `guest` | `/` | same | **ACTIVE, MINIMAL** | Only 8 routes — appears to be an early-stage or landing-focused surface, not a full parallel of the mobile app |
| `customer_app_mobile` | Customer Mobile App | React Native / Expo | `mobile/customer-app` | `expo start` | Same backend, mobile token storage | `customer`, `guest` | N/A (native navigation) | same | **ACTIVE, UNDER CONCURRENT CERTIFICATION** | 53 screens; currently being actively developed/certified by a separate, concurrent session under its own `CUSTOMER-L5-*` program (`docs/customer-app/`) — not touched by this sprint, per the mandatory non-interference practice established throughout this engagement |
| `staff_app_mobile` | Staff / Technician Mobile App | React Native / Expo | `mobile/staff-app` | `expo start` | Same backend | `staff`, `technician` | N/A | same | **ACTIVE, MINIMAL/EARLY** | Only 8 screens discovered — first time this app has appeared in any FINAL-L5 or MODULE-L5 inventory; genuinely under-certified relative to Super Admin |
| `e2e_admin_tenant` | Cross-app E2E harness | Playwright config/fixtures | `frontend/e2e-admin-tenant` | N/A (test harness, not a running app) | N/A | N/A | N/A | N/A | **TEST INFRASTRUCTURE, NOT A PRODUCT APPLICATION** | Excluded from the "6 applications" count below; recorded so it is not mistaken for an unknown 7th product app |

## Summary

- Applications discovered: **6** (5 product applications + 1 test-infrastructure directory correctly excluded from the product count)
- Active product applications: **5** (`super_admin`, `tenant_portal`, `customer_app_web`, `customer_app_mobile`, `staff_app_mobile`)
- Legacy/deprecated applications: **0** found
- Unknown applications: **0**

**Material finding**: `staff_app_mobile` (`mobile/staff-app`, 8 screens) is a genuinely new discovery for any L5-series inventory in this repository's history — no prior FINAL-L5-05 or CUSTOMER-L5 document references it. It is the least-certified application on the platform and should be prioritized early in the future module-sprint sequence (see `33-implementation-roadmap.md`).
