# Transaction and Concurrency Review — Workstream 6

## Pattern observed
Every mutation in `finance_hub/service.py` follows the same shape:
1. Load the target row (`_load_deposit`/`_load_payout`/etc.) within the
   request's existing DB session/transaction.
2. Read a `before` snapshot dict.
3. Mutate in-memory attributes.
4. `await self.db.flush()`.
5. `await self._audit(...)` within the same transaction.
6. Return the `after` dict.

No explicit row-level locking (`SELECT ... FOR UPDATE`) was found in any
of the 17 mutation paths. Commit boundaries are managed by the outer
request-scoped session (consistent with the rest of the codebase's
established pattern from prior slices — not unique to finance_hub).

## Concurrency risk assessment
A theoretical race exists wherever two concurrent requests load the same
row before either flushes (e.g., two simultaneous `approve_payout` calls
on the same `pending` payout could both pass `_require_status` before
either writes). This is a pre-existing, platform-wide pattern (identical
in every other engine audited across this slice series, e.g.
`tenant_engine`, `execution.home_service_router`) and was explicitly not
re-litigated or fixed in any prior slice — introducing row-locking here
would be a scope expansion (a product/infra-wide change) beyond a single
router's authorization slice, and no maker-checker or locking redesign
was requested. Logged as a known limitation, not fixed.

## Idempotency (concurrency-adjacent, in scope)
Three endpoints have genuine idempotency guards that mitigate the
practical impact of the race above:
- `record_offline_deposit`: reference-based dedup — a duplicate/concurrent
  call with the same `reference_id` is a no-op, not a double-credit.
- `retry_credit_posting`: `wallet_credit_status == "credited"` guard —
  blocks double-crediting, and the underlying `UsageCreditService` grant
  uses a stable idempotency key.
- `refund_topup` / `refund_deposit`: already-refunded guards prevent a
  second refund from being applied, though a true simultaneous race
  (both requests passing the check before either flushes) remains
  theoretically possible under the current lockless pattern.

## Conclusion
No conclusively provable, uniquely-finance_hub concurrency defect was
found. The general lack of row-locking is a platform-wide, pre-existing
pattern, not something introduced or discovered as unique to this
module — disclosed in `known-limitations.md`, not remediated here.
