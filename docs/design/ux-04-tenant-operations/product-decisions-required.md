# Product Decisions Required

1. Is there a real backend SLA/risk engine, or does `SLAStateView` need a
   product decision on where deadline/state computation happens (backend
   vs. frontend-derived from raw timestamps)? Currently 100% typed-fixture.
2. Booking Exception Resolution — still explicitly non-production; no
   change to that status this phase.
3. Customer cancel/reschedule for both pipelines — still unresolved;
   `cancelSupported: "unresolved_mock_only"` unchanged.
4. `TenantDetailPage` (UX-03) vs. the bespoke Job Detail Workspace layout —
   should the shared pattern be generalized to support 16 model-aware
   sections, or should operations workspaces keep a separate layout
   component going forward? (`shared-component-reuse-audit.md`)
5. Real `ServiceJob` status lifecycle — the brief's richer list
   (assigned/on_the_way/inspection/in_progress/work_done/completed) vs.
   the UX-03 fixture's narrower enum was not reconciled against
   `app/engines/home_service_assignment/models.py` /
   `app/engines/execution/models.py` this pass (see
   `job-list-specification.md`).
6. Dispute/complaint tenant authority boundary — confirm no tenant action
   ever issues a service credit or adjudicates a dispute, matching
   `DisputeView`'s current comments, once a real backend contract exists.
