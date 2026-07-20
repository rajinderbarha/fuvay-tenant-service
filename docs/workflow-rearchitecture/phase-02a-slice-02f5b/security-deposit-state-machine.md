# Security Deposit State Machine — Workstream 4

## Statuses observed
`unpaid`, `partially_paid`, `pending_verification`, `paid`, `partially_adjusted`,
`refunded`, `refund_requested`, `blocked`, `forfeited` (the last two are
read in `get_deposits_summary` but never written by any method in this
file — likely set by `package_commerce`'s `admin_adjust_deposit`, not
traced this slice, out of scope).

## Transitions implemented in `finance_hub.admin_router`

| Action | Precondition (before this slice) | Precondition (after this slice) | Result |
|---|---|---|---|
| `approve_deposit` | **none** | `status != "refunded"` (FIXED) | `status=paid`, `hold_state=held` |
| `reject_deposit` | none | none (unchanged — does not alter `status`, only `rejection_reason`) | metadata only |
| `record_offline_deposit` | positive amount + reference dedup (pre-existing) | unchanged | `status=paid` or `partially_paid` depending on `total_paid` vs `required_amount` |
| `refund_deposit` | positive amount + `status != "refunded"` (pre-existing) | unchanged | `status=refunded`, `hold_state=released` |
| `adjust_deposit` | delegates to `package_commerce` (not traced) | unchanged | `status=partially_adjusted` if `paid` and `current_balance < required_amount` |

## The defect found and fixed
`approve_deposit` had **no status precondition at all** — before this
slice, calling it on an already-`refunded` deposit would silently reset
`status` back to `"paid"` and `hold_state` back to `"held"`, illegitimately
reversing a refund that had already returned real money to the tenant.
This is inconsistent with every other terminal-state mutation in this
file (`refund_deposit` itself already blocks re-refunding; payouts use
`_require_status`; `settle_claim` blocks re-settling). **Fixed** by adding
the identical guard pattern `refund_deposit` already uses for itself:
reject with `DEPOSIT_ALREADY_REFUNDED` (409) if `status == "refunded"`.

## Repeated-operation safety after the fix
- `approve_deposit` on a refunded deposit: **now rejected** (was: silently
  succeeded, reversing the refund).
- `refund_deposit` on a refunded deposit: rejected (pre-existing).
- `record_offline_deposit` with the same reference twice: idempotent no-op
  (pre-existing, confirmed via reference-based dedup).

## Not verified this slice
`adjust_deposit`'s internal forfeiture/adjustment mechanism
(`package_commerce._commerce.admin_adjust_deposit`) was not traced — it is
outside `finance_hub` and `package_commerce.admin_router` was explicitly
out of scope for this slice.
