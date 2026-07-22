# Rating and Aggregate Integrity — Slice 2F-24

## Central finding: neither selected mutation touches any aggregate

Traced directly in source:

- `flag_review` -- creates a `ReviewFlag`, sets `status = flagged`, logs an
  event. **No call to `_trigger_aggregation`.**
- `submit_reply` -- creates a `ReviewReply`, logs an event, optionally
  notifies. **No call to `_trigger_aggregation`.**

Both asserted permanently by `TestRatingAggregateIntegrity`.

Aggregates (`TenantRatingSummary`, `StaffRatingSummary`) are recomputed only
from the review-status transitions owned by the admin surface --
`approve_review`, `reject_review`, `hide_review`, `delete_review` -- through
`_trigger_aggregation` -> `recompute_tenant_summary` /
`recompute_staff_summary`.

## Verification against each requirement

| Requirement | Result |
|---|---|
| Flagging cannot alter ratings through a foreign review | **MET twice over** -- foreign reviews are now unreachable, and flagging touches no aggregate even for an owned review |
| Repeated flagging does not repeatedly modify aggregates | MET -- vacuously; flagging never modifies them |
| Reply creation does not change rating values | MET -- verified in source |
| Publication changes update aggregates exactly once | MET -- recomputation is a full recompute from current rows, not an increment, so it is naturally idempotent |
| Invalid operations create no aggregate side effects | MET -- rejections raise before any write, and neither path reaches aggregation regardless |

## Why the pre-slice vulnerability was still serious

Flagging did not directly move a score, but `status = flagged` removes a
review from the approved population that recomputation counts. An attacker
could therefore not *set* a rating, but could influence which reviews remain
publicly visible -- and, on a competitor's tenant, at will. The fix closes it
at the ownership layer.

## Search ranking, badges, provider score, analytics
No route in scope writes to any of these. `recompute_tenant_summary` /
`recompute_staff_summary` are the only aggregate writers reachable from this
engine.

## Not redesigned
No rating formula was changed. The mission permits a correction only for a
proven integrity defect; none was found in the formulas themselves.
