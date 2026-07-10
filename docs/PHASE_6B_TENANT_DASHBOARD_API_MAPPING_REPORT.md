# Phase 6B Tenant Dashboard API Mapping

| Section | API Used | Endpoint |
|---------|----------|----------|
| Hero / Bookable Status | providerStatusApi.get() | GET /v1/provider/status |
| Setup Checklist | providerStatusApi.get() | GET /v1/provider/status |
| KPI: Bookable / Blockers | providerStatusApi.get() | GET /v1/provider/status |
| Finance: Usage Credit Balance | tenantSetupApi.getWallet() | GET /v1/provider/wallet |
| Finance: Package | tenantSetupApi.getPackage() | GET /v1/provider/subscription-status |
| Finance: Security Deposit | tenantSetupApi.getPackage() | GET /v1/provider/subscription-status |
| Staff Snapshot | staffApi.list() | GET /v1/auth/users?role=staff |
| Service Areas Snapshot | providerServiceAreasApi.list() | GET /v1/tenant/service-areas |
| Services Coverage | masterCatalogApi.listEnabled() | GET /v1/tenant/catalog/enabled-services |
| Recent Activity | tenantSetupApi.getActivity(1) | GET /v1/provider/activity?page=1 |
| Tenant Identity | localStorage | serviceos_tenant_name / serviceos_tenant_vertical |
