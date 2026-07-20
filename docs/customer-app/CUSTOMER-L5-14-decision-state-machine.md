# CUSTOMER-L5-14 — Decision State Machine

Source of truth: `app/engines/quote_checklist/constants.py`
`QUOTE_TRANSITIONS` (lines 19–32), enforced server-side by
`_assert_transition` (`quote_service.py` lines 62–65) on every mutating
call.

```
draft ──(staff: submit)──► submitted_to_provider ──(staff/admin: approve)──► provider_approved ──(staff: send)──► sent_to_customer
  │                              │                                              │
  └──(staff: send directly)──────┘                                             │
                                                                                 │
sent_to_customer ──(CUSTOMER: approve)──────► customer_approved  [FINAL]
sent_to_customer ──(CUSTOMER: reject)───────► customer_rejected  [FINAL]
sent_to_customer ──(CUSTOMER: request-revision)──► revision_requested ──(staff: mark_revised)──► revised ──► {submitted_to_provider | sent_to_customer}
sent_to_customer ──(no code path ever calls this)──► expired  [FINAL, unreachable — see baseline-verification.md #5.4]
(any non-final status) ──(staff: cancel)──► cancelled  [FINAL]
```

## This client's role

Only three of the above transitions are ever triggered by this
client — all three only from `sent_to_customer`:
`customer_approve` → `customer_approved`,
`customer_reject` → `customer_rejected`,
`customer_request_revision` → `revision_requested`. Every other
transition (`submit`, `send`, `mark_revised`, `cancel`) is staff/provider-
only and out of this client's scope entirely — this screen only ever
reads their results.

## Why `sent_to_customer` is the sole gate

`QUOTE_TRANSITIONS[q.status]` is the only set of valid `to_status`
values `_assert_transition` accepts; only `sent_to_customer`'s set
includes any of the three customer actions. Attempting any of them from
any other status raises `ERR_QUOTE_INVALID_TRANSITION` — which, per
baseline-verification.md #5.2, surfaces as an opaque 500, not a
meaningful 4xx. This client's `isQuoteActionable()`
(`domain/quote-state.ts`) enforces the identical gate before ever
enabling the corresponding button, so this failure mode should only ever
be hit by a genuine race (e.g. staff cancels the quote between this
screen's load and the customer's tap) — see
`financial-security-review.md`.
