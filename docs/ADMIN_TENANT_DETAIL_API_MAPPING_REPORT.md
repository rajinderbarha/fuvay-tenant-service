# Admin Tenant Detail — API Mapping Report

## Core Data Hooks

| Data | Hook | Backend Endpoint |
|------|------|-----------------|
| Tenant details | `tenantApi.get(id)` | `GET /v1/tenants/{id}` |
| Wallet/Credits | `commerceApi.walletBalance(id)` | `GET /v1/commerce/tenants/{id}/wallet` |
| Reviews aggregate | `reviewApi.getAggregate("tenant", id)` | `GET /v1/reviews/aggregate?entity_type=tenant&entity_id={id}` |
| Health | `tenantApi.getHealth(id)` | `GET /v1/tenants/{id}/health` |
| Billing info | `tenantApi.getBillingInfo(id)` | `GET /v1/tenants/{id}/billing` |
| Feature flags | `tenantApi.getFeatureFlags(id)` | `GET /v1/tenants/{id}/feature-flags` |
| Invoices | `tenantApi.getBillingInvoices(id, 5)` | `GET /v1/tenants/{id}/billing/invoices` |
| Jobs | `jobsApi.list({ tenant_id: id })` | `GET /v1/jobs?tenant_id={id}` |
| Bookings | `bookingsApi.list(id)` | `GET /v1/bookings?tenant_id={id}` |
| Staff | `staffApi.adminList(id)` | `GET /v1/admin/tenants/{id}/staff` |
| Users | `authApi.listUsers({ tenant_id: id })` | `GET /v1/auth/users?tenant_id={id}` |
| Service Areas | `serviceAreaAdminApi.listByTenant(id)` | `GET /v1/admin/service-areas?tenant_id={id}` |
| Enabled Services | `adminCatalogApi.listEnabledServices(id)` | `GET /v1/admin/catalog/enabled-services/{id}` |
| Security Deposit | `commerceApi.getDeposit(id)` | `GET /v1/commerce/tenants/{id}/deposit` |
| Packages | `commerceApi.listPackages()` | `GET /v1/commerce/packages` |
| Wallet Txns | `commerceApi.walletTransactions(id, 30)` | `GET /v1/commerce/tenants/{id}/wallet/transactions` |
| Media | `mediaApi.listFiles(id)` | `GET /v1/media/{tenant_id}/files` |
| Audit Log | `tenantApi.getAuditLog(id, { limit: 20 })` | `GET /v1/tenants/{id}/audit-log` |
| Engines | `engineMgmtApi.getEffectiveEngines(tenantId)` | `GET /v1/admin/engines/effective/{tenant_id}` |

## Mutation Endpoints (Fixed in Provider 360 Redesign)

| Action | API Call | Backend Endpoint | Status |
|--------|----------|-----------------|--------|
| Add Usage Credits | `adminTenantsApi.addUsageCredits(id, amount, reason)` | `POST /v1/admin/tenants/{id}/add-usage-credits` | ✅ Fixed |
| Suspend Tenant | `adminTenantsApi.suspend(id, reason)` | `POST /v1/admin/tenants/{id}/suspend` | ✅ Fixed |
| Reinstate Tenant | `adminTenantsApi.reactivate(id, reason)` | `POST /v1/admin/tenants/{id}/reactivate` | ✅ Fixed |
| Change Plan | `adminTenantsApi.changePlan(id, plan, reason)` | `POST /v1/admin/tenants/{id}/change-plan` | ✅ Fixed |
| Adjust Deposit | `commerceApi.adminAdjustDeposit(id, amount, reason, category)` | `POST /v1/commerce/tenants/{id}/deposit/adjust` | ✅ Existing |
| Request Changes | `adminTenantsApi.requestChanges(id, reason)` | `POST /v1/admin/tenants/{id}/request-changes` | ✅ Existing |
| Send Notification | `adminTenantsApi.sendNotification(id, subject, message)` | `POST /v1/admin/tenants/{id}/send-notification` | ✅ Existing |
| Export Report | `adminTenantsApi.exportTenantReport(id)` | `GET /v1/admin/tenants/{id}/export` | ✅ Existing |

## Spec vs Actual Mapping

The spec requested these sub-routes that don't exist as separate endpoints:

| Spec Route | Actual Source |
|-----------|---------------|
| `/v1/admin/tenants/{id}/summary` | Not needed — tenant detail from `GET /v1/tenants/{id}` |
| `/v1/admin/tenants/{id}/readiness` | Computed client-side from existing hooks |
| `/v1/admin/tenants/{id}/health` | `GET /v1/tenants/{id}/health` |
| `/v1/admin/tenants/{id}/jobs` | `GET /v1/jobs?tenant_id={id}` |
| `/v1/admin/tenants/{id}/bookings` | `GET /v1/bookings?tenant_id={id}` |
| `/v1/admin/tenants/{id}/finance` | Multiple: wallet + deposit + txns |
| `/v1/admin/tenants/{id}/audit` | `GET /v1/tenants/{id}/audit-log` or `GET /v1/admin/tenants/{id}/audit-logs` |
| `/v1/admin/tenants/{id}/media` | `GET /v1/media/{tenant_id}/files` |
