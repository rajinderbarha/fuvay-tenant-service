# FINAL-L5-03 — Target Architecture

## Confirmed: the existing architecture already matches the mission's recommended layering

```
Application Page
    -> Feature Hook (useApi/useAction)
    -> Feature API Module (e.g. serviceJobsApi, usageCreditsApi)
    -> Shared API Client (apiFetch, one per app)
    -> Backend Endpoint
```

For mutations:

```
Form / Action -> useAction -> API module -> apiFetch -> Backend
    -> .refetch() on the relevant useApi hook(s) for cache "invalidation"
    -> inline success/error UI feedback
```

This is not a new design decision this sprint — it is the pattern already established across every prior FINAL-L5-* sprint (confirmed via direct code reading, not assumed). This sprint's role was to **audit conformance to it**, not invent it.

## Frontend responsibilities (confirmed in-bounds this sprint)
Presentation, local interaction state, inline required/format validation, permission-aware rendering (via `isTenantReadOnly()`/`isTenantOwnerRole()`), API orchestration via `useApi`/`useAction`, loading/empty/error states.

## Backend responsibilities (confirmed authoritative, not duplicated in frontend — see Business Rule Duplication Report)
Business validation, authorization, tenant scoping, pricing calculations, matching rules, deduction calculations, idempotency, audit, persistence — all verified backend-only via the Business Rule Duplication scan this sprint.

## Forbidden frontend responsibilities — verified absent
- Calculating platform fees/deductions as authoritative logic: **not found** (frontend only displays `completion_data.collected_amount` and `usage_credit_balance`, both backend-computed).
- Determining tenant bookability without a backend response: **not found** (`providerStatusApi.get()`/bookability fields are always backend-sourced).
- Applying role authorization only in UI: **not found as a security gap** — UI-only checks exist (`isTenantOwnerRole`) but are explicitly UX-only; backend RBAC (verified extensively in FINAL-L5-01B/01D/02B) remains authoritative.
- Generating fake `request_id`: **not found**.
- Using dormant legacy tables through direct database access: **N/A for frontend** (frontend never touches the DB directly); on the backend, this sprint found and fixed a frontend *consumer* of a dormant-table-backed endpoint (`tenant_wallets` via `/v1/provider/wallet`) — see Business Rule Duplication / Deprecation Register.

## Result
Target architecture is documented and confirmed already in effect. No `NOT_READY` condition from this Part.
