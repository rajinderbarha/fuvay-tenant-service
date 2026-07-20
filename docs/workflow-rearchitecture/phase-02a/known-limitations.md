# Known Limitations

1. **My Work has no pagination.** Judged acceptable for a single technician's own job/parts-request count; will need pagination before extending to roles with larger result sets (admin, tenant_owner).
2. **My Work has no SLA data for the technician role.** None of the 4 minimum sources (job assigned, scheduled, inspection, quote) carry a real due-date/SLA concept beyond `ServiceJob.scheduled_date`, which is used as `due_at` but reported as `sla_state: "none"` rather than fabricating an SLA state with no backing policy.
3. **ESCALATED and RECENTLY_COMPLETED categories are unpopulated.** No real data source was identified for either within this phase's scope (technician role, ServiceJob + PartsRequest only) — rather than inventing one, these sections simply don't render when empty (the frontend already filters empty sections out).
4. **No install action for technicians on approved parts requests.** Only the provider/tenant-side `/v1/provider/service-jobs/{id}/parts-requests/{id}/install` endpoint exists. This is reported to the technician honestly via `recommended_action` text rather than hidden or faked.
5. **Notification and audit behavior for parts-request state changes is unverified**, not confirmed present or absent in the reviewed code path. No notification/audit claim was added to the UI.
6. **No frontend priority filter control**, though the backend query param and its filtering logic are tested — a UI control for it was cut from scope.
7. **Pre-existing duplicate-operation-ID warnings** in `service_setup/templates_router.py` remain (see `regression-test-report.md`) — unrelated to this phase, not fixed.
8. **No live HTTP integration test** (real server + real DB) was run for the new endpoint — only mocked-DB unit tests plus a static route-registration check.
9. **No frontend component/E2E test** was added for the new My Work page or Parts Request form — verified via TypeScript compilation only.
10. **Two existing routers both mount `POST /v1/staff/service-jobs/{job_id}/accept`** (`home_service_assignment/staff_router.py` and `execution/home_service_router.py` — confirmed during Phase 1A's route dump). This pre-existing duplication was not touched or investigated further this phase.
