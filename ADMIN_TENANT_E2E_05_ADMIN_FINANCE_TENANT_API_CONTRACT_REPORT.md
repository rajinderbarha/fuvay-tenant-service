# ADMIN-TENANT-E2E-05 — Admin Finance/Tenant API Contract Report

## Endpoints actually used by the pages in scope
| Endpoint | Method | File | Used by |
|---|---|---|---|
| `/v1/admin/tenants/{tenant_id}/usage-credit-ledger` | GET | `app/engines/tenant_engine/admin_router.py:333` | `/admin/finance/usage-credits`, `/admin/tenants/{id}` Finance→Usage Credit Ledger tab |
| `/v1/admin/tenants/{tenant_id}/add-usage-credits` | POST | `admin_router.py:314` | "Add Usage Credits" form on both surfaces above |
| `/v1/admin/finance/wallets` (list) + `/v1/admin/finance/wallets/{wallet_id}` | GET | `financeApi.listWallets` | `/admin/finance/wallets` (separate system, see below) |
| `/v1/admin/tenants` (list) | GET | `adminTenantsApi.list` | `/admin/tenants` |
| `/v1/admin/tenants/{id}` + ~20 tab-specific endpoints | GET | `tenantApi.get` + per-tab hooks | `/admin/tenants/{id}` |
| `/v1/admin/home-services/*` (service/pricing-rule config) | GET | `homeServicesCatalogConsoleApi` + `catalogApi.listPricingRules` | `/admin/home-services/completed-job-deduction` |

## Real finding: THREE parallel wallet/credit endpoint families exist server-side
1. `GET/POST /{tenant_id}/usage-credit-ledger`, `/add-usage-credits` — authoritative for Home Services, backs `tenant_billing.credit_balance` (3958.00 for demo tenant). **This is what the in-scope pages use.**
2. `GET /{tenant_id}/wallet`, `/wallet/ledger`, `POST /wallet/topup`, `/wallet/adjust` (same file, `admin_router.py:653-700+`) — a **second, parallel** credit-wallet API family in the *same router*, reading `tenant_wallets` (0.00 for demo tenant). Not called by any page in scope for this sprint; confirmed via grep that neither `usage-credits/page.tsx` nor `tenants/[id]/page.tsx`'s `wallet` hook calls these paths.
3. A comment at `admin_router.py:650-651` references `app/engines/package_commerce/admin_router.py` registering the **same paths a third time** ("never reachable while these existed" — see `PHASE_4_FINANCE_BUG_FIX_REPORT.md` from an earlier sprint), i.e. there is a known, previously-documented route-shadowing bug in this exact area.

## Contract correctness for in-scope pages
- Request/response shapes match: `UsageCreditLedgerEntryAdmin` (frontend type) lines up with what `get_usage_credit_ledger` returns (job_id, event_type, credit_delta, balance_before/after, deduction_source, request_id).
- Tenant scoping: `get_usage_credit_ledger` filters by `.where(UsageCreditLedger.tenant_id == tenant_id)` from the path param — no cross-tenant leakage possible via this endpoint (see Isolation report).
- Auth: `add_usage_credits`/ledger read require `get_current_user`; `wallet/topup`/`adjust` (the parallel family) require `require_super_admin` — inconsistent auth strictness between the two families, another sign they are separately maintained/legacy vs. current.

## Verdict: PASS for the endpoints actually exercised by in-scope pages (correct, tenant-scoped, consistent contract). The dormant `/wallet*` endpoint family and the previously-documented route-shadowing note are real, pre-existing technical debt — flagged, not fixed (out of this sprint's scope, which is to verify the real routes, not rebuild the legacy wallet engine).
