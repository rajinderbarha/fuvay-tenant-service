# Legacy Aggregate Integrity — Slice 2F-25

## What touches aggregates

`_recompute_aggregate` is invoked from the review lifecycle transitions
(creation and resolution), not from flagging or replying. Verified in source.

| Operation | Aggregate effect |
|---|---|
| `submit_reply` | **none** |
| `flag_review` | **none** — writes status/reason/actor + history only |
| `resolve_flag` (publish/remove) | recomputed — platform admin only |
| `create_review` | recomputed — route is 410, so unreachable from HTTP |

## Verification

| Requirement | Result |
|---|---|
| Flagging cannot alter ratings through a foreign review | **MET twice** — foreign reviews unreachable, and flagging touches no aggregate |
| Repeated flagging cannot repeatedly modify aggregates | MET — second flag raises CONFLICT before any write |
| Reply creation does not change rating values | MET |
| Aggregates updated exactly once where applicable | MET — recomputation is a full recompute, naturally idempotent |
| Invalid operations create no aggregate side effects | MET — rejections raise before any write |

## Pre-computed by design
The engine's own contract is that the aggregate read never runs `AVG()` at
read time. That design is unchanged; this slice added no aggregate write path
and changed no formula.

## Tests
Covered indirectly by the no-persistence assertions in
`TestMutationAuthority`; the flag path is asserted to reach neither `db.add`
nor `db.commit` on denial.
