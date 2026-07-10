# ADMIN_TENANT_E2E_01 — Admin Login Browser Report

Test: `frontend/e2e-admin-tenant/e2e/admin-tenant-foundation.spec.ts` →
"super admin can log in via browser and reach dashboard" (`E2E_APP=admin`)

## Steps performed (real browser, real backend)
1. `page.goto('/login')` on real Next.js dev server (port 3000, system Chrome via `channel: 'chrome'`)
2. Filled email `admin@serviceos.in` / password `Password123!`, clicked submit
3. Asserted URL left `/login` and now matches `/admin/...`
4. Asserted rendered body text does NOT contain a raw JWT string
5. Asserted at least one real `/v1/...` network request was observed (captured via `page.on('request')`)
6. Screenshot saved: `frontend/e2e-admin-tenant/evidence/admin-login-dashboard.png`
7. Request log saved: `frontend/e2e-admin-tenant/evidence/admin-login-requests.json`

## Result
PASS. `POST /v1/auth/login` observed in the request log; redirect to the admin dashboard confirmed;
no visible JWT in rendered DOM text.
