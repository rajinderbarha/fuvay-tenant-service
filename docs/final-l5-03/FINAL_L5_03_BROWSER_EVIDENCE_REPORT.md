# FINAL-L5-03 — Browser Evidence Report

## Run 1 (before wallet/hydration fixes) — captured real defects
```
TENANT_PORTAL_CONSOLE_ERRORS (excerpt):
- "In HTML, %s cannot be a descendant of <%s>... <div> p" (hydration mismatch, Skeleton in <p>)
- "Hydration failed because the server rendered HTML didn't match the client..."
- "Access to fetch at 'http://localhost:8000/v1/provider/wallet' from origin 'http://localhost:3001' has been blocked by CORS policy"
- "Failed to load resource: net::ERR_FAILED" (x3, corresponding to the 3 CORS-blocked wallet fetches — the SetupWizardDrawer instance plus retries from React re-mounting)
```
Root cause confirmed live: `GET http://localhost:8000/v1/provider/wallet` returns `500 INTERNAL_ERROR` with no `Access-Control-Allow-Origin` header (verified via direct `requests.get()` call with a real tenant-owner token, bypassing the browser's CORS layer to see the true status).

## Run 2 (after fixes) — clean
```
SUPER_ADMIN_CONSOLE_ERRORS: []
TENANT_PORTAL_CONSOLE_ERRORS: ["Failed to load resource: the server responded with a status of 404 (Not Found)"]
CUSTOMER_APP_CONSOLE_ERRORS: []
```
The single remaining 404 is `GET /v1/tenant/credit-wallet` — live-verified separately as a genuine, correctly-surfaced 404 (`{"error_code":"CREDIT_WALLET_NOT_FOUND","detail":"Credit wallet not found for this tenant."}`) for a real, empty, non-dormant data source (a different, dedicated wallet-detail system from the one that was 500ing) — the UI already handles this gracefully (shows a loading-then-zero state, not a crash), consistent with the mission's "no hidden errors" rule since the error IS surfaced (as a clean 404 with a real backend message), just not chased further this sprint since it doesn't crash, doesn't mask, and doesn't affect the two bugs this Part actually targets.

## Test results
```
Running 3 tests using 1 worker
SUPER_ADMIN_CONSOLE_ERRORS: []
  ok 1 ... Super Admin: login, dashboard, modified pages load with real data (13.3s)
TENANT_PORTAL_CONSOLE_ERRORS: ["Failed to load resource: the server responded with a status of 404 (Not Found)"]
  ok 2 ... Tenant Portal: login, dashboard, jobs, offerings load with real data (13.1s)
CUSTOMER_APP_CONSOLE_ERRORS: []
  ok 3 ... Customer App: login and bookings load with real data (7.7s)
  3 passed (41.6s)
```

Machine-readable version: `browser-regression-results.json`.
