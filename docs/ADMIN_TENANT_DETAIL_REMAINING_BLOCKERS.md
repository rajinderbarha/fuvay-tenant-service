# Admin Tenant Detail — Remaining Blockers

## P0 Blockers
None.

## P1 Items (Non-blocking)

### 1. Provider Readiness — No Dedicated Backend Endpoint
**Status:** Computed client-side from existing hooks.
**Impact:** Readiness calculation uses multiple hooks (zones, enabledSvcs, pricing, staff, packages, deposit, wallet, tenant). These hooks all load independently; first-paint readiness reflects whichever data has loaded.
**Mitigation:** All hooks load eagerly on page mount. No mock data used.

### 2. Audit Tab Uses `/v1/tenants/{id}/audit-log` Not `/v1/admin/tenants/{id}/audit-logs`
**Status:** Both endpoints exist. The tenant engine audit-log endpoint is used. The admin audit-logs endpoint at `/v1/admin/tenants/{id}/audit-logs` is also present.
**Impact:** Audit data comes from the correct source; endpoint naming difference only.

### 3. Permission-Aware Guards — No Backend Permission Token
**Status:** The spec calls for `admin.tenants.credits.add` etc. permission checks. The admin portal does not have a granular permission system in the current JWT — all admin users have the same access level.
**Impact:** All admin action buttons are shown to all admin users. No UI hiding based on missing permissions.
**Mitigation:** All mutations are gated on the backend by `require_admin_user`.

## P2 Items (Nice-to-have)

### 1. Dedicated `/v1/admin/tenants/{id}/readiness` Endpoint
Would allow server-side readiness calculation with more accurate data.

### 2. Circular Progress Animation on Load
Current CircularProgress SVG is static (no CSS animation on mount).

### 3. Mobile Layout for Hero Card
Actions collapse to More menu on mobile but the hero still shows all badges which could be crowded on small screens.
