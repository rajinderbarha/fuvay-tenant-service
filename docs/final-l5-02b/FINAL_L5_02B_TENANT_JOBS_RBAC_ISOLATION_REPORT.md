# FINAL-L5-02B — Tenant Jobs RBAC and Isolation Report

Live probe against `/v1/provider/my-records/jobs*` this sprint, real accounts, real tokens.

| Role | List result | Detail result | Expected | Match |
|---|---|---|---|---|
| Tenant Owner | 200, `items:5, total:5` | 200, real job data | own-tenant read access | Yes |
| Tenant Read Only | 200, `items:5, total:5` | (not separately probed via API; browser-confirmed read access + mutation controls absent) | read permitted | Yes |
| Wrong Tenant (`owner@isolation-test-services.local`) | 200, `items:0, total:0` | 200, `{"error":"FINAL_JOB_NOT_FOUND"}` (embedded, no data) | 403 or secure 404 | **Isolation holds (0 data exposed), but literal status code is 200 not 403/404 — same pre-existing L5-01D-006 pattern, not a new finding** |
| Customer | 200, `items:0, total:0` | not probed (customer has no valid job_id to try) | 403 | **Isolation holds (0 data exposed), same status-code caveat** |
| Technician (same tenant) | not separately probed this sprint (documented in FINAL-L5-01D as legitimate same-tenant access, not a violation) | — | same-tenant access permitted | Carried, unchanged |
| Anonymous | 401 | — | 401 | **Exact match** |

## Cross-tenant response field leak check
Inspected the actual JSON body of the Wrong-Tenant detail response: `{"success": true, "data": {"error": "FINAL_JOB_NOT_FOUND"}}` — **zero fields from the real job** (no `job_number`, `customer_id`, `status`, address, or any other data) are present. No leak.

## Result
Isolation is real and enforced (verified by inspecting response bodies, not just status codes). The one honest caveat — non-tenant/non-owner requests return HTTP 200 with an embedded not-found error rather than a literal 403/404 — is the same L5-01D-006 pattern already known and carried forward, not a new isolation failure, and does not trigger `NOT_READY_FINAL_L5_02B_CUSTOMER_ISOLATION_FAILED` (that status is reserved for actual data exposure or broken customer-side isolation, which Part 16 covers separately).
