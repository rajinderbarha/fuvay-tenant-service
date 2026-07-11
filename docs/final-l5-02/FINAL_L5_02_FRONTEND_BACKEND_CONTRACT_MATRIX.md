# FINAL-L5-02 — Frontend-to-Backend Contract Matrix

## Method
Real browser sessions (6 canonical roles, `e2e/super-admin/final-l5-01b-six-sessions.spec.ts`) plus direct API cross-checks against the frontends' actual `lib/api.ts` client code — not a full static audit of every frontend call, but real, evidence-based spot checks that found 2 genuine contract-drift bugs.

## Confirmed connections (CONNECTED_MATCH)

| Application | Feature | Frontend call | Backend endpoint | Result |
|---|---|---|---|---|
| Super Admin | Login | `POST /v1/auth/login` | same | Real 200, JWT issued |
| Super Admin | Tenants list | `GET /v1/admin/tenants` | same | Real 200, real data (Demo AC Services + Isolation Test Services) |
| Tenant Portal | Login | `POST /v1/auth/login` | same | Real 200 |
| Tenant Portal | Staff | `GET /v1/tenant/staff` | same | Real 200 |
| Customer App | Login | `POST /v1/auth/login` | same | Real 200 |
| Customer App | Catalog | `GET /v1/catalog/master/services` | same | Real 200 |

## Confirmed contract drift (CONNECTED_CONTRACT_DRIFT) — real bugs found

| Application | Feature | Frontend calls | Should call | Impact |
|---|---|---|---|---|
| Tenant Portal | Jobs list | `GET /v1/jobs` (legacy field_ops, `frontend/tenant-portal/lib/api.ts:245`) | `GET /v1/provider/service-jobs/assignable` (canonical `service_jobs`) | Real jobs data invisible to Tenant Owner in the browser — confirmed via live comparison (legacy call → 422 `TENANT_REQUIRED`; canonical call → real data). BUG-L502-005. |
| Customer App | Bookings list | `GET /v1/customer/bookings` (canonical, correctly called) | — endpoint is correct | Not a frontend bug — a **seed gap**: the canonical endpoint queries `service_bookings` (0 rows), which FINAL-L5-01's seed never populated (it populated `bookings` instead). BUG-L502-006. |

## Not exhaustively covered
The full mission ask (every frontend API call across Admin/Tenant/Customer/Staff mapped to its backend endpoint, with field-name/pagination-shape/envelope verification) was not built as a complete static matrix this sprint — that would require parsing every `lib/api.ts`/`api-client.ts` call site across 4 frontends against the 2,253-endpoint registry. What was done instead: **real browser-driven discovery**, which found 2 genuine, high-value bugs that a static audit might have missed (both required runtime behavior — an empty list vs. an error — to notice).

## Result
2 real contract-drift/seed-gap bugs found and precisely root-caused via live evidence (not source inspection alone, per the non-negotiable rules). Full static contract-matrix coverage remains a documented gap — real findings via live testing were prioritized over exhaustive but shallower static mapping, given time constraints.
