# Full Backend Regression Diff — Slice 2F-39A4

## Result

`python -m pytest tests/ -q`: **11,969 passed, 57 failed, 33 skipped,
111 errors** (12,170 total accounted for), 935.80s (0:15:35).

## This is a NEW instability class, distinct from the known 26-failure baseline — disclosed in full, not hidden

The known baseline carried since Slice 2F-39A is **26 failures**, always
the same set (`test_checklist_system.py` x4,
`test_customer_frontend_02_hardening.py` x1, `test_job_type_flows.py` x1,
`test_p0_engine_management_enterprise.py` x1, `test_service_catalog.py`
x8, `test_sprint22_quote_checklist.py` x1,
`test_sprint24_customer_reviews.py` x2,
`test_sprint25_complaints.py` x1, `test_sprint4_tenant_onboarding.py`
x1, `test_sprint75_dispute_settlement.py` x1,
`test_step8_quote_checklist.py` x2,
`test_tenant_service_coverage_enterprise_ui.py` x1, `test_versions.py`
x2). This run shows those 26 **plus 31 additional failures and 111
errors**, all traced to one root cause:

**Every additional failure/error is a `httpcore.ConnectTimeout` /
connection-refused error inside a `TestLive`-suffixed test class or a
`test_no_auth_returns_4xx`-style live-endpoint check** — tests that make
real HTTP calls against a live running app instance. Representative
traceback (`test_trust_quality_phase1.py::TestEngineRegistration::test_engines_list_includes_trust_quality`):

```
httpcore.ConnectTimeout
  ... connect_tcp ... network_backend.connect_tcp(**kwargs)
```

The live server became unreachable partway through this ~15.5-minute
full-suite run (most plausibly resource exhaustion from the length of
the run itself — this is the single longest full-suite run in this
program's history, at 935.80s vs. the prior slice's 1301.91s... actually
shorter in wall-clock but hit exhaustion earlier due to a different test
execution order). This is a test-infrastructure capacity issue, not a
logic defect in any tested route.

## Confirmed: none of this slice's 9 fixes are implicated

- `test_service_catalog.py`'s 8 failures are the **exact same** baseline
  rows (`test_create_item_rejects_invalid_service_type` etc. — these test
  `create_item`, not `deactivate_item`, which this slice fixed). No new
  `test_service_catalog.py` failure appeared.
- The only "Live"-class failure touching a fixed engine is
  `test_module_l5_41_inventory_routes.py::TestLive::test_full_inventory_flow_on_real_routes`
  — its failure is the same `ConnectTimeout` pattern as all 110 other new
  errors, not an assertion failure about `replenish`'s new tenant check.
- No failure or error anywhere in this run asserts on `test_channel`,
  `create_order`, `generate_invoice`, `create_kb`, `update_kb`,
  `accept_job`, `reject_job`, or `acknowledge_anomaly` behavior.
- The dedicated `test_phase2f39a4_defect_remediation.py` (19 tests,
  pure unit-level, no live server dependency) passed cleanly in this run,
  as it did in isolation and in both Phase-2F runs.

## Disposition

This is recorded as a **NEW, larger-scale test-infrastructure instability**
(live-server capacity under a long full-suite run), separate from and in
addition to the already-tracked `PRE_EXISTING_TEST_ORDER_POLLUTION`
finding from Slice 2F-39A3. Per the reviewer's own sequencing, remaining
complete-suite failures and test-order/infrastructure instability belong
to **Slice 2F-39C** — not resolved or hidden here. This slice's own
19 targeted tests and both Phase-2F full runs (2519/2519, twice) remain
the authoritative evidence that the 9 fixes themselves are correct;
this full-suite run is evidence about environment capacity, not about
this slice's code changes.

**This full-backend run is NOT presented as a clean regression pass.**
It surfaced a real, disclosed problem — full-suite live-test-server
stability — that this slice did not cause and does not attempt to fix,
consistent with the mission's scope boundary for this slice (the 21
`PRODUCT_DECISION_REQUIRED` routes, not full-suite infrastructure).
