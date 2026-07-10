# HS8 — Test Results

## Targeted sweep
```
pytest tests/ -k "assignment or execution or sprint20 or sprint21 or home_service_booking or hs7 or hs8" -q
```
Initial run: **5 failed, 283 passed.** All 5 failures in
`test_sprint21_execution.py` were a direct, confirmed consequence of this
pass's own fix — converting bare `ValueError` raises to
`ServiceOSException` (needed to make invalid-transition/not-found/
reason-required errors surface as clean 422s instead of raw 500s). Tests
asserted `pytest.raises(ValueError)` and checked `str(exc.value)`; updated
to `pytest.raises(ServiceOSException)` and `exc.value.error_code`,
documented inline with the reasoning.

Re-run: `tests/test_sprint21_execution.py` → **72 passed, 0 failed.**

## Full targeted sweep re-run
Not re-run in full after the test-file fix (time budget); the specific
file containing all 5 original failures is confirmed 100% green, and no
other production files were touched after that fix.

## TypeScript / build / lint / frontend tests
Not run — no frontend code exists for the tenant job queue, technician
app, or admin operations dashboard this ticket describes.

## Verdict
Backend: clean after fixing the 5 tests that were asserting the
pre-fix (bare-ValueError) error contract.
