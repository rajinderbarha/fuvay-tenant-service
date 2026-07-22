# No-Partial-Persistence Proof

Every provenance rejection scenario introduced or re-verified this slice raises `ServiceOSException` before any `db.add`/`db.flush`/`db.commit` call:

| Rejection scenario | Test | Persistence proof |
|---|---|---|
| Wrong-customer actor (field_ops relationship) | `test_field_ops_relationship_denies_when_query_scoped_to_target_customer` | `db.add.assert_not_called()` |
| Provider-created booking, no bound match, no independent evidence (convert_to_job) | `test_convert_to_job_creator_check_uses_bound_query_not_role_alone` | `db.add.assert_not_called()` |
| All 14 legacy-row scenarios in `legacy-fail-closed-matrix.csv` | Inherited from 2F-15A/2F-15B's `db.add.assert_not_called()` proofs, re-verified unaffected by the actor-binding change (mock shapes updated where the query's return type changed, behavior unchanged) | `db.add.assert_not_called()` |

For every scenario:
- The existing Booking row is unchanged (no `UPDATE` statement reached).
- No Job, assignment, checklist item, success-history row, success audit/domain event, or notification is created — all downstream mutation code in the affected methods runs strictly after the provenance checks (source-position unchanged from 2F-15A/B, only the query's internal filter tightened).
- No commit precedes rejection.

The actor-binding fix is a stricter WHERE-clause filter on existing read-only queries — it introduces no new write path and cannot itself cause partial persistence; it can only cause MORE rejections (never fewer), which is the intended direction for a security-hardening change.
