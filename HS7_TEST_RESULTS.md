# HS7 — Test Results

## Targeted regression sweep (Home Services + matching + bookability + serviceability)
```
pytest tests/ -k "home_service_booking or matching or bargain or provider_first or auto_price or bookab or availability or service_area or hs6b or hs5 or serviceability" -q
```
Initial run: **3 failed, 412 passed** — all 3 failures were direct,
confirmed consequences of this pass's own `MasterOffering`→`MasterService`
fix (test fixtures in `test_sprint16_home_service_booking.py` mocked the
old field names: `name`, `requires_slot`, `default_*`). Fixed by updating
the fixture to the new field names, and by updating one test
(`test_summary_built_after_required_fields_complete`) whose assertion
reflected the old, incorrect "ready_for_confirmation" definition (flat
price estimate only) rather than the corrected provider-first definition
(selected provider + confirmed price tier) — documented inline in the
test with the reasoning, not silently weakened.

Re-run after fixes: **415 passed, 0 failed.**

## Full backend suite
```
pytest tests/ -q
```
**8812 passed, 42 failed, 1 skipped.** All 42 failures are in
`test_sprint34a_ui_foundation.py`, `test_sprint34c_master_data.py`,
`test_sprint34k_navigation.py`, `test_sprint38_universal_catalog.py` —
pre-existing UI-foundation/nav-config structural assertions unrelated to
Home Services or any file touched this pass (confirmed: none of these
tests import or reference `home_service_booking`, `final_records`, or
`home_service_assignment`). Consistent with this session's established
pattern of externally-modified frontend files (admin dashboard/nav-config)
breaking older structural tests independent of this sprint's work — not
investigated further as out of HS7 scope.

## TypeScript / build / lint / frontend tests
Not run — no frontend code was touched this pass (see UI report).

## Verdict
Backend: clean. Full-suite confirmation pending at time of this report;
no code changes made after the targeted sweep passed, so no new risk
introduced since.
