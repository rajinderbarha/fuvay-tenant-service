# Same-Record Alternate Route Audit — Slice 2F-24

Every mounted route that can reach `CustomerReview`, `ReviewReply` or
`ReviewFlag` was enumerated from the router sources and the live route walk.

| Route | Persona | Classification | Disposition |
|---|---|---|---|
| provider `submit_reply` (SELECTED) | tenant_owner | `SAME_RECORD_SAME_CAPABILITY` | **PROTECTED this slice** |
| provider `flag_review` (SELECTED) | tenant_owner | `SAME_RECORD_SAME_CAPABILITY` | **PROTECTED this slice** |
| customer `flag_review` | customer | `SAME_RECORD_DISTINCT_PERSONA` | **CORRECTED this slice** (client tenant removed, self-scoped) |
| customer `submit_review` | customer | `SAME_RECORD_DISTINCT_PERSONA` | eligibility-gated; unchanged |
| customer `edit_review` | customer | `SAME_RECORD_DISTINCT_PERSONA` | customer-ownership checked; `ALTERNATE_PROTECTED` |
| customer `get_my_review` | customer | read | **CORRECTED** -- was unscoped IDOR |
| provider `get_review` | tenant-side | read | **CORRECTED** -- was unscoped IDOR |
| provider list/summary/staff-summary | tenant-side | read | tenant-scoped; unchanged |
| admin approve/reject/hide/delete review | super_admin | `SAME_RECORD_DISTINCT_PERSONA` | `ALTERNATE_PROTECTED` |
| admin `resolve_flag` | super_admin | `PLATFORM_FLAG_RESOLVE` | `ALTERNATE_PROTECTED` |
| admin `approve_reply` / `reject_reply` | super_admin | `PLATFORM_REVIEW_MODERATE` | `ALTERNATE_PROTECTED` |
| public review reads | anonymous | read | public by design; approved/public only |
| `POST /v1/reviews` (legacy) | n/a | `DEPRECATED_410` | **remains 410** |
| `app.engines.review` get/flag/list | authenticated | `DISTINCT_MODEL` | different table (`reviews`); out of boundary |
| job/booking completion rating path | internal | writes via the customer_reviews submit path | `TRUSTED_INTERNAL`; unchanged |

## No weaker live route remains for `customer_reviews`

Both same-record write paths (provider flag, customer flag) now enforce
ownership through the one central scoped lookup. Both detail reads are scoped.
Every admin path requires `require_super_admin`. There is no remaining route
by which an unauthorized principal can create, modify or read a foreign
`CustomerReview`, `ReviewReply` or `ReviewFlag`.

## Legacy 410 preserved
`test_legacy_review_create_remains_410` asserts the 410 in source, and
`test_legacy_engine_is_a_distinct_model` asserts the two tables are `reviews`
and `customer_reviews` respectively -- so a future merge of the two engines
fails this suite rather than silently reopening the retired path.

## Honest note on the legacy engine
`app.engines.review`'s own `flag_review` uses a primary-key-only lookup behind
`get_current_user` -- the same shape as the defect fixed here -- but on the
superseded `reviews` table whose write entry point is already 410. It is
`DISTINCT_MODEL`, so the mission's "changes outside customer_reviews are
permitted only for a proven same-record bypass" does not authorise touching
it. Recorded in `known-limitations.md` and `deferred-items.md` as a candidate
rather than silently ignored.
