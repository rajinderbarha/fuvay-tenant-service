# Notification Chat-Access Investigation

## Both failures: resolved this slice, non-authorization-defect

| Field | `test_chat_thread_customer_cannot_access_other_customer` | `test_chat_thread_provider_cannot_access_other_tenant` |
|---|---|---|
| Deterministic | Yes | Yes |
| Passes in isolation | Yes (fails the same way whether run alone or in the full suite — not order-dependent) | Yes |
| Depends on test order | No | No |
| Real authorization defect? | **No** | **No** |
| Category | Stale test expectation (error-message string) | Stale test expectation (error-message string) |

## Root cause

`app/engines/platform_notifications/chat_service.py::ChatThreadService.validate_thread_access`
was deliberately changed (by an earlier, unnamed slice — the code's own
comment references "the established Booking-series precedent") to raise
`ERR_CHAT_THREAD_NOT_FOUND` for **both** "thread doesn't exist" and
"thread exists but caller isn't authorized" cases, rather than the older
`ERR_CHAT_THREAD_ACCESS_DENIED` for the latter. This is a **non-oracular
privacy improvement**: an unauthorized caller can no longer distinguish
"that thread doesn't exist" from "that thread exists and isn't yours" —
exactly the same pattern this program enforces for Booking, N01 media,
and other object-ownership checks elsewhere.

**Access was and remains correctly denied in both cases** — both tests'
`pytest.raises(ValueError, ...)` block always fired; only the expected
match string was stale.

## Resolution

Both tests updated to assert `ERR_CHAT_THREAD_NOT_FOUND` instead of
`ERR_CHAT_THREAD_ACCESS_DENIED`, preserving their real intent (customer
cannot access another customer's thread; provider cannot access another
tenant's thread) — see commit `f2cdb4a`. All 44 tests in
`test_sprint27_notifications.py` now pass.

## No fix was needed to application code

`chat_service.py` itself was not modified — its behavior is already
correct and was already correct before this slice (the "regression" was
entirely in the test's expectation, not the code).
