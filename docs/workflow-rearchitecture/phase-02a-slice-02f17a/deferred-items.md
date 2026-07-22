# Deferred Items

Per this slice's explicit OUT OF SCOPE list, the following remain deferred:

- Implementation of `app.engines.platform_notifications.provider_router` (confirmed selected) — deferred to Slice 2F-18.
- All 10 non-selected modules — queued in `application-wide-module-queue.csv`, not implemented.
- Any new role, permission, or migration.
- Any pipeline merge (`Booking`/`ServiceBooking`, `field_ops.Job`/`ServiceJob`).
- Any `PartsRequest` or `quote_checklist` modification.
- `My Work` / `Next-Action` aggregation.
- Booking Exception Resolution.
- Frontend/UI work of any kind.
- Remediation of `readonly@demo-ac-services.local` (confirmed untouched).
- Application of Migration 144 (confirmed unapplied).
- A full manual, line-by-line business-capability review of all ~1186 mounted mutation routes' source code (the discovery this slice performed relies on the path-prefix heuristic plus the existing `guard_status`/exemption-list machinery — see `known-limitations.md`).
- Fixing the pre-existing, unrelated `test_phase2d_tenant_access_model.py` stale-assertion failure (honestly reported in `regression-report.md`, not caused by this slice, out of this discovery slice's scope to fix).
- A full application-wide customer-mutation and platform-admin-mutation census beyond the aggregate counts already reported by the runtime tool (see `known-limitations.md`).
