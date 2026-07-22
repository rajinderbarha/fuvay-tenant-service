# Documentation Corrections — Slice 2F-20

## Forward annotation to Slice 2F-19
Added a "Forward annotation (added by Slice 2F-20)" section to
`docs/workflow-rearchitecture/phase-02a-slice-02f19/approval-gate.md`,
confirming 2F-19's module selection
(`app.engines.compliance.provider_router`) was implemented and CORRECT,
not corrected — no change to 2F-19's own findings was needed.

## Self-corrections made during this slice's own drafting

1. **`compliance-request-state-machine.csv`** — an early draft incorrectly
   stated that `customer_tenant_response` and `staff_tenant_response` do
   NOT write an audit event. Direct code read
   (`grep -n "_audit(" app/engines/compliance/provider_router.py`)
   confirmed both routes DO call `_audit(...)` (lines ~793, ~903). The
   CSV row was corrected before finalizing, with an explicit note
   distinguishing the correction from the earlier draft.

2. **`runtime-verification-report.md`** — an early draft implied
   `download_export`'s guard_status was confirmed via the
   `inventory_mutation_routes.walk()` runtime tool, matching the other 6
   routes. Re-verification showed the walker only tracks
   POST/PUT/PATCH/DELETE routes; `download_export` is a GET and never
   appears in its output. Corrected to clarify that `download_export`'s
   dependency was instead confirmed via the test suite's direct
   source-level introspection of the route's `dependant` tree.

No other canonical CSV or prior-slice document required correction.
Both canonical CSVs (`tenant-mutation-endpoint-inventory.csv`,
`mutation-enforcement-matrix.csv`) were updated as part of this slice's
own intended coverage change (200 → 206 / 226), not as a correction of
prior-slice error.
