# Quote / Inspection / Checklist Boundary — Slice 2F-13 (Workstream 15)

## Distinct workflows, distinct models (verified separation preserved)

| Concept | Model / router | Relationship to this router |
|---|---|---|
| Field-ops checklist TEMPLATE (this slice) | `ServiceChecklistTemplate`/`ServiceChecklistItem`, `checklist_router` | canonical template administration |
| Per-job checklist EXECUTION | `JobChecklistItem`, `field_ops.service.py`/`staff_router` | SAME_MODEL_DISTINCT_CAPABILITY-adjacent (distinct model, distinct capability) — out of scope |
| Quote checklist / customer quote approval | `JobQuote` + FieldOpsService customer quote flow (`test_step8_quote_checklist.py`, `test_sprint22_quote_checklist.py`) | DISTINCT_MODEL_DISTINCT_CAPABILITY — the canonical customer quote workflow is quote_checklist, NOT this router and NOT parts_request (established finding, preserved) |
| Inspection checklist | no dedicated `InspectionChecklist` model exists | DISCONNECTED (absent) |
| Parts checklist / PartsRequest | PartsRequest (ServiceJob-scoped) | DISTINCT — PartsRequest boundaries unchanged (preserved) |

## Preserved established finding
The real customer quote workflow is **quote_checklist** (`JobQuote` +
FieldOpsService), **not** parts_request and **not** this template router.
This slice did not merge quote approval into this module, did not merge
inspection/quote/completion models, and did not touch quote_checklist or
parts_request.

## Conclusion
This router (`ServiceChecklistTemplate`) is cleanly separated from quote,
inspection, and job-execution checklists. No merge occurred.
