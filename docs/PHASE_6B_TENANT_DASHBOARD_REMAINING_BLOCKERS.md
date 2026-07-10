# Phase 6B Tenant Dashboard Remaining Blockers

## P0 Blockers
None.

## P1 Notes
- Security deposit fields (security_deposit_status, security_deposit_amount) are derived from the package/subscription-status endpoint. If the backend does not return these fields, the deposit card will show "₹5000 / Pending" as a safe fallback. Backend may need to add these fields to /v1/provider/subscription-status response.
- The `tenantSetupApi.getActivity()` endpoint at /v1/provider/activity may not exist on all deployments. The component handles this gracefully (shows "No recent activity" empty state).

## P2 Notes
- Staff snapshot shows UserDetail (email, full_name, role, is_active) from /v1/auth/users. The `full_name` may be null for users who haven't completed their profile; falls back to email.
- Setup checklist completion percentage is client-side computed from blocker arrays + live API counts, not a single backend field. This is intentional — the backend ProviderStatusResult does not expose a setup_completion_percent field.
