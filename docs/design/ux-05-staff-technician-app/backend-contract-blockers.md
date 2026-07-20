# Backend Contract Blockers

Found by reading `src/lib/api.ts` in full and cross-checking against the brief's assumed workstreams. None of these
were fabricated as endpoints in this phase's code — every screen/component touching them is explicitly tagged
`api_contract_required`/`mock_design_only`.

| Blocker | Impact | Current handling |
|---|---|---|
| No StaffPermission-fetch endpoint | Staff Work Queue / Parts Approval / permission-gated Home cannot show real grants | `permissionsFor()` returns an explicit all-denied MOCK_DESIGN_ONLY set |
| No role field on StaffUser | Cannot distinguish staff vs technician from real data | `deriveRole()` fails closed to `technician` |
| No parts-request endpoint at all | Items 14–16 (creation/tracking/approval) have zero real backend surface | `PartsRequestShowcaseScreen` is dev-only, local-state, clearly labeled |
| No inspection-content endpoint | `startInspection`/`completeInspection` are state transitions only, no form payload | `InspectionDraftView` typed but no live adapter built this pass |
| No checklist-content endpoint | Same as inspection | `ChecklistExecutionView` typed but no live adapter built this pass |
| No quote endpoint | Item 17 has no real backend surface | `QuoteSummaryView` typed but no live adapter built this pass |
| No dedicated availability endpoint (available/busy/on_job/off_duty) distinct from job status | Item 21 not concretely buildable against real data | `AvailabilityView` typed; deferred |
| `jobsApi.complete`/`accept`/`reject` have no idempotency key | Offline-replay would be unsafe | Documented as `online_required`, never auto-retried, in `offline-operation-matrix.csv` |
| Staff-app earnings (per MODULE-L5-33 memory) points at a dead table | Pre-existing, not re-verified this pass | Left untouched; flagged in `existing-screen-route-audit.csv` disposition `PRODUCT_DECISION_REQUIRED` |
