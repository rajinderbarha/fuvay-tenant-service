# ServiceOS — Final Tenant Isolation Report

**Date:** 2026-07-03
**Sprint:** 36 (verification only)
**Source:** Sprint 31 Security Hardening + Sprint 32 Smoke Testing

---

## Isolation Model

ServiceOS is a multi-tenant platform. Each tenant is a business (e.g., "AC Repair Co."). The isolation requirement is:

> **No tenant should ever see another tenant's data — under any circumstances.**

This is enforced at the database query level, not the application or frontend level.

---

## How Isolation Is Enforced

### 1. JWT Claims as Source of Truth
Every authenticated request contains a JWT with `tenant_id` (for tenant-scoped users) or `customer_id` (for customers). These values are:
- Set at login time from the database
- Signed with `JWT_SECRET_KEY`
- Verified on every request by `get_current_user` dependency
- **Never overridden by request body, query params, or headers**

### 2. TenantScopeService
Applied on all admin/tenant-owner routes. Example pattern:
```python
async def get_my_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    scope = TenantScopeService(current_user)
    query = select(Job).where(Job.tenant_id == scope.tenant_id)
    ...
```

The `scope.tenant_id` is derived from the JWT — never from the request.

### 3. Cross-Tenant IDOR Test (Sprint 32)
A test was written and passed where:
- Tenant A is logged in
- The request attempts to access Tenant B's resource by ID
- The API returns 403 or 404 (not the resource)

This confirms that even if an attacker guesses a resource UUID belonging to another tenant, the query-level filter prevents access.

---

## Isolation Coverage by Resource Type

| Resource | Isolation Method | Verified |
|----------|-----------------|---------|
| Jobs / Service Jobs | `tenant_id` in WHERE clause via TenantScopeService | Yes |
| Invoices | `tenant_id` scoped; Sprint 32 P0 fix confirmed | Yes |
| Staff Members | `tenant_id` foreign key + scope service | Yes |
| Provider offerings | `tenant_id` on all pcat/offering tables | Yes |
| Bookings | `customer_id` via CustomerScopeService (customer view) | Yes |
| Reviews | `tenant_id` on review tables | Yes |
| Complaints | `tenant_id` scoped | Yes |
| Analytics reports | `tenant_id` in all aggregation queries | Yes |
| AI conversations | `customer_id` scoped; history isolated per customer | Yes |
| Wallet/commission | `tenant_id` on all financial tables | Yes |
| Notifications | `tenant_id` + recipient scoping | Yes |
| Audit logs | `tenant_id` scoped; admin reads all, tenant reads own | Yes |

---

## Known Gaps

- **Super admin** can see all tenant data by design — this is correct behavior; super admin endpoints are guarded by `role=super_admin` JWT claim check
- **Cross-tenant admin access** is not possible via normal tenant-owner JWT; would require compromising super_admin credentials

---

## Security Rules Confirmed Active

From Sprint 31 code review (still in place as of Sprint 36):

1. No tenant sees another tenant's data — enforced at DB layer
2. No customer sees another customer's data — CustomerScopeService on all customer routes
3. No provider accesses admin-only data — router separation + require_technician dependency
4. Frontend hiding is not security — backend enforces all access
5. No trust of tenant_id/customer_id from request body
6. No provider API accepts tenant_id override
7. No customer API accepts customer_id override
8. Password hash / tokens / OTP / API keys never exposed in responses
9. Authentication not disabled on any production endpoint
10. **Tenant isolation failure is P0 release blocker** — no such failures found in Sprint 36 audit
