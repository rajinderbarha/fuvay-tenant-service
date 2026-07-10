# ADMIN_TENANT_E2E_01 — Backend + DB Health Report

## GET /health
```
{"status":"ok","version":"2.4.1","environment":"development", ...
 "services":[{"service":"postgresql","status":"ok","latency_ms":9.69},
             {"service":"redis","status":"ok","latency_ms":1.24}],
 "engines":{"total":35,"core":19,"plugin":16, ...}}
```
Backend healthy, Postgres and Redis both `ok`, 35 engines registered and healthy.

## Real endpoints verified (spec's example paths were illustrative; corrected against actual code)
- Admin overview/dashboard data: served under `/admin/dashboard` frontend page via
  `dashboard_command_center` and `analytics` engines — confirmed reachable in-browser (Part 9).
- Tenant readiness/checklist: real endpoint is `GET /v1/tenant/dashboard/runtime`
  (`app/engines/tenant_engine` / `provider_portal`), confirmed via curl:
  ```
  {"success":true,"data":{"tenant":{"tenant_id":"34b427a7-...","business_name":"Demo AC Services",
   "category":null},"category_type":"home_services", ...},
   "meta":{"request_id":"req_0c357dd9a4ac", ...}}
  ```
  Also `/v1/provider/business-profile` (GET/PUT), used in Parts 5 and 8.
- Auth: `POST /v1/auth/login` — verified for 7 distinct users (super admin, admin operator, tenant
  owner, tenant manager, tenant read-only, staff, customer), all returned `success:true` with a JWT.
- request_id on errors: confirmed present on a real 404 response:
  ```
  {"type":"https://serviceos.io/errors/NOT_FOUND","status":404,"error_code":"NOT_FOUND",
   "request_id":"req_68ce5443b3cf"}
  ```
  and on a real 200 mutation response's `meta.request_id` (`req_b5b3f05ceaec`).

## Result
PASS — real backend, real Postgres, real Redis, real auth, real request_id propagation confirmed.
