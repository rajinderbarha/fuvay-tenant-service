# Amount and Currency Integrity — Workstream 6

## Amount validation by endpoint

| Endpoint | Amount source | Validation |
|---|---|---|
| `record_offline_deposit` | client-supplied | positive-amount check (pre-existing); accumulated against `required_amount` |
| `refund_deposit` | client-supplied | positive-amount check + capped implicitly by already-refunded guard (pre-existing) |
| `adjust_deposit` | client-supplied | delegated to `package_commerce` (not traced) |
| `retry_credit` | server-derived (`credits_purchased` + `bonus_credits` read from the topup row, not client input) | no client amount to validate — immune to client-side amount tampering by construction |
| `refund_topup` | client-supplied | positive-amount check + capped at `amount_paid` (pre-existing) — cannot over-refund |
| `approve_payout` | client-supplied `approved_amount`, defaults to requested amount if omitted | no explicit upper-bound check against the original requested amount was found beyond the default; not flagged as a defect this slice since payout mutations remain super-admin-only under the interim policy (lower urgency), but noted in `known-limitations.md` |
| `assign_reviewer`, `request_documents`, `reject_deposit`, `mark_processing`, `mark_completed`, `mark_failed`, `reject_payout` | n/a | no amount involved |
| `approve_claim`, `reject_claim` | client-supplied `amount_approved` | delegated to `package_commerce` (not traced) |
| `settle_claim` | server-derived (`settled_amount = c.amount_approved`, not client-supplied) | immune to client-side tampering by construction |

## Currency
No multi-currency handling was found anywhere in `finance_hub` — all
amounts are treated as a single implicit currency (consistent with the
rest of the platform as observed in prior slices). No currency-mismatch
defect is possible because no currency field is read or compared in this
module.

## Findings
- The one confirmed integrity defect (`approve_deposit`'s missing
  final-state guard) was a **state** defect, not an amount defect, and is
  already fixed (see `security-deposit-state-machine.md`).
- `approve_payout`'s unbounded `approved_amount` (when explicitly supplied
  by the caller, rather than defaulted) is a **potential** finding but was
  not conclusively provable as an exploitable defect within this slice's
  evidence (the endpoint is super-admin-only, and no counter-evidence of
  an intended cap was found in the model or nearby code) — logged as a
  known limitation, not remediated, per the "close only conclusively
  proven defects" instruction.
