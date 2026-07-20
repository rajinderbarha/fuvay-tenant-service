# Deprecated Security-Deposit Routes — Workstream 8

## The 4 routes (1 GET + 3 mutations)
`admin_get_deposit` (GET), `admin_mark_deposit_paid` (POST),
`admin_refund_deposit` (POST), `admin_forfeit_deposit` (POST) — all under
`/v1/admin/tenants/{tenant_id}/security-deposit*`.

## Verified behavior (re-confirmed this slice, unmodified)
Each handler body is exactly:
```python
async def admin_xxx(tenant_id: uuid.UUID, request: Request) -> dict:
    from fastapi import HTTPException
    raise HTTPException(status_code=410, detail=_DEPOSIT_BLOCKED_DETAIL)
```
- **No `Depends()` of any kind** — no DB session, no auth dependency, no
  service instantiation. The function raises before any authorization
  check, any database query, or any service-layer call could occur.
- **No write occurs**: confirmed both by source inspection (no `db.add`/
  `db.execute`/`db.commit` in the function body) and by a new regression
  test (`TestDeprecatedSecurityDepositRoutes::test_no_db_mutation_occurs`)
  that asserts a mocked DB session's `execute`/`add`/`commit` are never
  called when hitting these routes.
- **No frontend caller remains**: re-confirmed via grep of
  `frontend/super-admin` — zero references to any of these 4 paths.
- **Canonical replacement**: the response detail message explicitly
  points to `app.engines.finance_hub` (`/v1/admin/finance/deposits*`),
  confirmed still correct and unchanged by Slice 2F-5B's own closure of
  that module.
- **OpenAPI marking**: the route summaries are prefixed
  `"[DEPRECATED_410]"` in the `summary=` field, which surfaces in the
  generated OpenAPI schema — visible to any spec consumer.
- **No hidden alternate implementation**: `PackageCommerceService.admin_mark_deposit_paid`/
  `admin_refund_deposit`/`admin_forfeit_deposit` still exist as *methods*
  in `service.py` (lines 511-565) but are called by **zero** routers
  anywhere in `app/` (confirmed via grep) — they are orphaned, unreachable
  code, not a live tenant-accessible bypass. See
  `package-commerce-service-bypass-report.md`.

## Tenant-role reachability
Because these 4 routes have no auth dependency at all, technically an
unauthenticated caller (of any role or none) reaches the `raise
HTTPException(410, ...)` line — but since this happens before any data
access, there is no information disclosure or mutation risk. This is
confirmed safe by design, not a gap: 410 is returned identically
regardless of caller identity, and no tenant data is ever touched.

## New regression tests added this slice
- 410 status for all 4 routes, called with **no** authentication override
  at all (proving the 410 fires before the auth layer, consistent with
  having no `Depends()`).
- No DB mutation (`execute`/`add`/`commit` never called) for the 3 POST
  routes, using the shared mocked-DB fixture.
- Source-inspection test confirming none of the 4 handlers call `_svc(...)`.

## Conclusion
All 4 routes remain inert, exactly as adjudicated in the prior slice.
Not deleted (per instruction). No change made.
