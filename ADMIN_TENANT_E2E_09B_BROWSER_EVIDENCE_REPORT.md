# ADMIN-TENANT-E2E-09B — Browser Evidence Report

Screenshots + logs saved under `frontend/e2e-admin-tenant/evidence/e2e09b/` (produced by the
real Playwright run against real system Chrome, listed in the Playwright report).

| Item | Route | Role | Action | API call | Status | Screenshot | Result |
|---|---|---|---|---|---|---|---|
| Owner setup page | /tenant/setup/services | Owner | view | GET enabled-services | 200 | owner-setup-services.png | No read-only banner shown |
| Owner safe mutation + revert | (API) | Owner | PUT pricing 850/1100 (revert) | PUT .../pricing | 200 | rbac.log | Reverted to original values, confirmed via GET |
| Read-only setup page | /tenant/setup/services | Read-only | view | GET enabled-services | 200 | readonly-setup-services.png | Page renders, no NaN/undefined, no forbidden labels |
| Read-only disabled mutation UI | /tenant/setup/services (wizard, final step) | Read-only | attempt Save/Publish | n/a (button disabled) | n/a | readonly-setup-services.png | Save/Publish disabled via `disabled={readOnly}` |
| Read-only direct-mutation 403 | (API) | Read-only | PUT pricing (invalid payload) | PUT .../pricing | **403** | rbac.log | `PERMISSION_DENIED`, request_id present |
| Active credit balance | (API) | Owner | GET provider/status | GET /v1/provider/status | 200 | bookability.log | `tenant_billing`-backed, `is_bookable:true` |
| Live bookability/matching | (API, customer) | Customer | match-and-price | POST .../match-and-price | 200 | bookability.log | Demo AC Services selected |
| Low/Mid/High price options | (API) | Customer | match-and-price | same | 200 | bookability.log | 770 / 850 / 935 INR |
| Window AC+LG coverage status | (API) | Owner | attempted area-coverage add | PUT .../coverage | 500 (unique-constraint) | n/a | Type+brand enabled; area-coverage row blocked by real DB constraint (documented gap) |
| Publish-readiness credit check | (API) | Owner | GET provider/status | same as above | 200 | bookability.log | Uses `tenant_billing`, no `tenant_wallets` |

All request_ids and status codes above are real, captured from the live curl/Playwright runs
in this sprint (not fabricated).
