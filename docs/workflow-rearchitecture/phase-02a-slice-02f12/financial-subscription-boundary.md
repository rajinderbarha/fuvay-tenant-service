# Financial/Subscription Boundary — Slice 2F-12 (Workstream 13)

## Search performed
Grepped `coaching_router.py`, `coaching_service.py`, and
`CoachingAppointment`'s model fields for fee/deposit/subscription/
package/discount/scholarship/refund/payment/wallet/credit/payout/
commission terminology.

## Findings
- **`CoachingAppointment.appointment_fee_snapshot`** is an
  **informational JSONB snapshot** captured at draft-confirmation time —
  read-only from this module's perspective; no route in
  `coaching_router.py` reads, writes, or mutates it.
- **No fee, deposit, subscription, refund, wallet, credit, payout, or
  commission capability exists anywhere in this module or its connected
  service** — confirmed absent, not merely unused.
- **No financial ledger service is imported or called** by
  `coaching_service.py`.

## Requirements review
- Course/consultation fee is not treated as a real payment — N/A, no
  fee-mutation concept exists in this router.
- No new monthly-subscription behavior was introduced.
- No cash refund or payout behavior was invented.
- No unguarded wallet/credit/deposit mutation is reachable from this
  module — confirmed, none exists.

## Conclusion
This workstream's target risk (a weaker real-money path) does not exist
in this module. Nothing to fix, nothing to block closure on this basis.
