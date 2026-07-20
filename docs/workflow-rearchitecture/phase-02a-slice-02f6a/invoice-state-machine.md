# Invoice State Machine — Workstream 5

## Statuses (from `constants.py`, re-verified unchanged)
`draft`, `issued`, `payment_pending`, `payment_collected`, `paid`,
`cancelled`, `failed`.

## Legal transitions (`INVOICE_TRANSITIONS`, unchanged this slice)
```
draft             -> {issued, cancelled}
issued            -> {payment_pending, payment_collected, paid, cancelled}
payment_pending   -> {payment_collected, paid, failed, cancelled}
payment_collected -> {}  (terminal)
paid              -> {}  (terminal)
cancelled         -> {}  (terminal)
failed            -> {issued}
```

## Verified behavior

| Rule | Status |
|---|---|
| Invoice creation produces the correct initial state | YES — `create_invoice` always sets `status=INV_DRAFT` |
| Items can be changed only in allowed states | YES — `add_item` requires `status == draft` (unchanged; pre-existing) |
| Issue can occur only from the correct state | YES — `_assert_transition(inv, INV_ISSUED)` checks `INVOICE_TRANSITIONS` (pre-existing); re-verified this slice with a direct test forcing `status=cancelled` |
| Issue cannot occur twice | YES — explicit `if inv.status == INV_ISSUED: raise` guard (pre-existing), directly tested this slice |
| Empty invoice cannot be issued unless explicitly allowed | **Not enforced** — `issue_invoice` does not check whether the invoice has any line items. Not fixed this slice: no evidence this is unintended (an invoice can legitimately represent a job with a single flat service charge seeded via `_copy_from_booking`, and "empty invoice" is not itself a proven defect) — logged as a known limitation. |
| Cancelled invoice cannot be issued | YES — `_assert_transition` rejects `cancelled -> issued` (not in the transition set), directly tested this slice |
| Paid invoice cannot be modified | YES — `add_item` only allows `status == draft`; `payment_collected`/`paid` are terminal states with no further-mutation path in this module |
| Payment cannot occur before the permitted state | **FIXED this slice** — `record_onsite_payment` previously had no invoice-status precondition at all; now requires `status in (issued, payment_pending)` |
| Tenant and ServiceJob linkage remains valid | YES — `issue_invoice` re-syncs `ServiceJob.status` to `JOB_STATUS_INVOICE_ISSUED` in the same transaction (pre-existing, unmodified) |

## Conclusion
The one genuine state-machine defect (`record_onsite_payment`'s missing
invoice-status precondition) is fixed. No other transition-model defect
was found; the state model itself was not changed, per "do not change
the state model unless a clear defect is proven."
