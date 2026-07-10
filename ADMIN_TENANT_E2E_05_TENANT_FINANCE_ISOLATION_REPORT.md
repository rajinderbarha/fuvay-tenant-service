# ADMIN-TENANT-E2E-05 — Tenant Finance Isolation Report

## Platform data reality
`SELECT count(*) FROM tenants;` → **1** (only "Demo AC Services" exists). This means a real cross-tenant leak cannot be demonstrated empirically with a second live tenant in this environment — isolation is therefore verified at the query/code level instead.

## Code-level isolation verification
`GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` (`app/engines/tenant_engine/admin_router.py:333-345`):
```python
.where(UsageCreditLedger.tenant_id == tenant_id)
```
`tenant_id` is bound directly from the URL path parameter (a `uuid.UUID` FastAPI-validated type) — every query is scoped by an explicit tenant filter, not by an implicit session/global scope that could accidentally widen. Same pattern confirmed for `add_usage_credits` (line 314+).

## Frontend isolation
- `/admin/finance/usage-credits`: tenant ID is a single input field, pre-filled but editable — an admin viewing a different tenant ID gets a fresh fetch scoped to that ID only; no client-side caching observed that would bleed one tenant's ledger into another's view (each `Load Ledger` click re-fetches via `getTenantLedger(tenantId)`).
- `/admin/tenants/{id}` Finance tab: `id` comes from the Next.js dynamic route segment; the `wallet` hook is keyed by `[id]` in its `useCallback`/`useApi` dependency array (`app/admin/tenants/[id]/page.tsx:1067`), so navigating between two tenant IDs correctly re-fetches rather than reusing stale data.

## DB-level guard (bonus finding, not isolation but related integrity)
`uq_ucl_job_event_once` — a `UNIQUE (job_id, event_type) WHERE event_type='completed_job_deduction'` constraint — prevents the same job from ever being double-deducted, which also indirectly prevents any accidental cross-tenant duplicate-posting scenario since `job_id` is itself tenant-scoped.

## Verdict: PASS at the code/query level (every finance/tenant read/write for usage credits is explicitly filtered by a tenant_id bound from the request, no global/session-implicit scope found). Could not be empirically re-verified with a second real tenant because only one exists in this environment — flagged as a residual gap for a future sprint that seeds a second tenant specifically for isolation testing.
