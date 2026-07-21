# Test-Order Root Cause

## Symptom

`tests/test_phase2f35_critical_authorization_batch.py::TestDocumentTenantAuthority::test_generate_document_calls_trusted_tenant`
failed only when run as part of the full 12,096-test suite; passed every
time in isolation or within `tests/test_phase2f*.py` alone.

## Root cause (found and fixed)

`tests/test_dispatch_job_sync.py::test_invoice_generated_transition_actually_creates_a_document`
monkeypatches `DocumentService.generate_document` and `DocumentService.__init__`
directly onto the class (not via `unittest.mock.patch` context manager, nor
`monkeypatch` fixture) to stub out document generation for its own test.
Its `finally` block restored `__init__` but never restored
`generate_document` — permanently replacing the real method with the test
stub for the remainder of the pytest process. Any later test in the same
process that calls `inspect.getsource(DocumentService.generate_document)`
(as the target test does) inspects the stub's source instead of the real
implementation, and fails.

This is a genuine test-isolation defect: global mutable state (a class
attribute) was patched without a corresponding, reliable restore.

## Investigation method

1. Confirmed the target test fails only in full-suite context, passes
   alone (baseline reproduction).
2. Searched all test files referencing `DocumentService` — found exactly
   one (`test_dispatch_job_sync.py`).
3. Read that file's monkeypatch/teardown code directly — found the
   asymmetry (restores `__init__`, not `generate_document`) by inspection,
   not by bisection.
4. Fixed by capturing and restoring both attributes in the `finally`
   block.
5. Verified by running the polluting test immediately before the
   previously-failing test in the same pytest invocation — now passes.

## Why not a workaround

No retry, forced ordering, skip, timeout, or assertion weakening was used.
The actual mutable global state (the class attribute) is now correctly
restored, which is the real fix — the same guarantee holds regardless of
what order pytest happens to run tests in.

## Stability proof

`pytest tests/test_dispatch_job_sync.py
"tests/test_phase2f35_critical_authorization_batch.py::TestDocumentTenantAuthority"`
(the exact polluting-then-polluted pairing) — all `TestDocumentTenantAuthority`
tests pass, confirmed via `-v` output. Not separately re-verified across
the full 12,096-test suite a second time this slice (see
`complete-backend-regression-report.md` for the one full run performed).
