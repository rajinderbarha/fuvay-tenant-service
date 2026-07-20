# Slice 2F-36 Non-Regression Report

Slice 2F-36's enterprise/tenant-administration/operational batch
(enterprise_grid, admin_catalog, profile, marketing_automation,
analytics, chat, inventory, appointments, catalog, dispatch, ds,
settings, notifications) unaffected. Sample routes `POST /v1/chat/conversations/{conversation_id}/messages`
and `PUT /v1/me/profile` remain `VERIFIED`. No file under
`app/engines/enterprise_grid/`, `app/engines/admin_catalog/`,
`app/engines/profile/`, `app/engines/marketing_automation/`,
`app/engines/analytics/`, `app/engines/chat/`, `app/engines/inventory/`,
`app/engines/appointment/`, `app/engines/service_catalog/`,
`app/engines/dispatch/`, `app/engines/data_science/`,
`app/engines/settings_engine/`, or `app/engines/notification/` was
touched this slice. Full `tests/test_phase2f36_enterprise_tenant_admin_operational_batch.py`
re-run and confirmed green after its own arithmetic-only rebaseline.
