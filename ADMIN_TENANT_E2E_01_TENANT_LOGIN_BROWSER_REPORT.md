# ADMIN_TENANT_E2E_01 — Tenant Login Browser Report

Test: `admin-tenant-foundation.spec.ts` → "tenant owner can log in via browser and reach
dashboard/setup" (`E2E_APP=tenant`)

## Steps performed
1. `page.goto('/login')` on real Next.js dev server (port 3001, system Chrome)
2. Filled email `provider@serviceos.in` / password `Password123!`, submitted
3. Waited for and asserted the rendered page contains the literal text "Demo AC Services"
4. Asserted no raw JWT visible in body text
5. Asserted a real `/v1/auth/login` request was observed
6. Screenshot: `frontend/e2e-admin-tenant/evidence/tenant-login-dashboard.png`
7. Request log: `frontend/e2e-admin-tenant/evidence/tenant-login-requests.json`

## Real bug found and fixed during this test
On first run, the dashboard showed the placeholder "Your Business" instead of "Demo AC Services".
Root cause in `frontend/tenant-portal/app/login/page.tsx`: after login, the code fetched
`GET /v1/tenant/dashboard/runtime` and looked for `rdata.tenant_name` (flat), but the real API shape is
`data.tenant.business_name` (nested):
```
{"data":{"tenant":{"tenant_id":"...","business_name":"Demo AC Services"},"category_type":"home_services"}}
```
Because the flat key never existed, the code silently fell back to the logged-in user's `full_name`
(via `localStorage.setItem("serviceos_tenant_name", u?.full_name ?? "")`), which is not the tenant name.
Fixed by reading `rdata.tenant?.business_name ?? rdata.tenant_name`. Verified via a debug Playwright
script that `localStorage.getItem('serviceos_tenant_name')` now returns `"Demo AC Services"` after login,
and the foundation test now passes.

## Tenant context correctness
No cross-tenant leakage observed — the only tenant name rendered is "Demo AC Services", matching
`provider@serviceos.in`'s own `tenant_id`.

## Result
PASS (after the fix above). Bug fixed in `frontend/tenant-portal/app/login/page.tsx`.
