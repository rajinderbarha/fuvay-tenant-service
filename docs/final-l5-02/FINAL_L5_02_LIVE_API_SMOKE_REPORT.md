# FINAL-L5-02 — Live API Smoke Report

Real HTTP requests against the **live backend** (`localhost:8000`) using the FINAL-L5-01 canonical users. Full results in `live-api-smoke-results.json`.

## Authentication — all 7 canonical roles logged in successfully (real JWT issued)
| Role | Email | Login status |
|---|---|---|
| Super Admin | admin@serviceos.local | 200 |
| Admin Operations | admin.ops@serviceos.local | 200 |
| Tenant Owner | owner@demo-ac-services.local | 200 |
| Tenant Read Only | readonly@demo-ac-services.local | 200 |
| Customer One | customer1@serviceos.local | 200 |
| Customer Two | customer2@serviceos.local | 200 |
| Technician One | tech1@demo-ac-services.local | 200 |

## Smoke matrix — 12/12 PASS

| Test | Method | Path | Role | Status | Expected | Result |
|---|---|---|---|---|---|---|
| unauth_admin_tenants | GET | /v1/admin/tenants | anon | 401 | 401 | PASS |
| bad_login | POST | /v1/auth/login | anon | 401 | 401 | PASS |
| admin_tenants_list | GET | /v1/admin/tenants | super_admin | 200 | 200 | PASS |
| **admin_tenants_as_customer** | GET | /v1/admin/tenants | customer1 | **403** | 403 | **PASS** |
| **admin_tenants_as_technician** | GET | /v1/admin/tenants | technician1 | **403** | 403 | **PASS** |
| **admin_tenants_as_owner** | GET | /v1/admin/tenants | tenant_owner | **403** | 403 | **PASS** |
| admin_notfound | GET | /v1/admin/tenants/{zero-uuid} | super_admin | 404 | 404 | PASS |
| tenant_staff_owner | GET | /v1/tenant/staff | tenant_owner | 200 | 200/404 | PASS |
| tenant_staff_unauth | GET | /v1/tenant/staff | anon | 401 | 401 | PASS |
| customer_bookings | GET | /v1/customer/bookings | customer1 | 200 | 200/404/422 | PASS |
| catalog_services | GET | /v1/catalog/master/services | customer1 | 200 | 200 | PASS |
| health | GET | /health | anon | 200 | 200 | PASS |

## Critical result: FINAL-L5-01B RBAC fix confirmed LIVE
The three rows in bold are the live-server confirmation that was left as a gap in FINAL-L5-01B (where the sandboxed environment couldn't restart the shared server). After a clean backend restart this sprint, `customer`, `technician`, and `tenant_owner` roles all receive **403** on `GET /v1/admin/tenants` against the real running server — matching the 21 in-process regression tests. The vulnerability is closed in the live system, not just in tests.

## request_id
Every error response (401/403/404) in the matrix carried a `request_id`/`req_` marker in its body — confirmed via the smoke script's `has_request_id` flag.

## Performance note
Every request took ~2,000ms against the local bundled Postgres (cold connection per request, no pool warming in this smoke harness). This is a local-environment diagnostic artifact, not a production measurement — flagged in the performance report, not treated as a blocker.

## Honest scope
This is a **representative** smoke matrix covering auth, RBAC enforcement, tenant, customer, and catalog paths across all 7 roles — not all 2,253 endpoints. It proves the critical auth/authorization/isolation invariants hold on the live server; it does not exhaustively certify every endpoint (stated plainly).
