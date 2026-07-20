# CUSTOMER-L5-11 — Conversion Contract

## Source Draft Status

`HomeServiceBookingDraft.status` must be `"ready_for_confirmation"`
(set by `mark_ready_for_confirmation`, itself gated on real
serviceability/provider/price-tier checks) — enforced by
`finalize()`'s own guard (`if draft.status != _READY: raise ValueError(ERR_DRAFT_NOT_READY)`).
An idempotent retry (draft already `"confirmed"`) skips this guard
entirely and short-circuits to the dedup lookup instead
(contract-matrix.md).

## Fields Copied into `ServiceBooking` (verbatim, from the draft)

`draft_id` (`draft.id`), `customer_id`, `tenant_id` (=
`draft.selected_tenant_id`), `category_id`, `offering_id`,
`ai_session_id`, `customer_name`, `customer_phone`, `city`, `zipcode`,
`address_snapshot`, `preferred_date`, `preferred_time_window`,
`issue_summary`, `issue_details`, `provider_snapshot` (=
`draft.selected_provider_snapshot`, **unstripped** — see
security-review.md).

## Fields Derived/Constructed (not a direct copy)

- `booking_number` / (on the sibling `ServiceJob`) `job_number` —
  freshly generated (`BK-YYYYMMDD-NNNNNN`/`JOB-YYYYMMDD-NNNNNN`), never
  present on the draft.
- `price_snapshot` — a **new** object, not a direct copy of
  `draft.price_snapshot`: `{...draft.price_snapshot,
  selected_price_option: booking_summary.selected_price_tier,
  selected_price_amount: booking_summary.customer_offer, payment_mode:
  "customer_pays_provider_directly"}` — the real, disclosed reason (per
  the code's own "HS7 fix" comment) is that the customer's tier choice
  lived only in the ephemeral `booking_summary` blob, never in
  `price_snapshot` itself, until this fix copied it across so
  post-booking screens can show which tier was chosen without needing the
  now-terminal draft.
- `status` — set to the real, only-observed initial value
  `"pending_assignment"` (a fixed literal in `finalize()`, not derived
  from any draft field).

## `ServiceJob` (created 1:1 alongside every booking)

Not a direct draft copy either — constructed fresh with `booking_id`
(referencing the just-created `ServiceBooking`), `customer_id`,
`tenant_id`, `category_id`, `offering_id`, `scheduled_date`/
`scheduled_time_window` (from `draft.preferred_date`/
`preferred_time_window`), `city`/`zipcode`/`address_snapshot` (same
source), `status: "pending_assignment"`. This client does not build any
job-status UI this sprint (out of explicit scope) — the confirmation
screen's `job` field (from `GET /bookings/{id}`) is fetched and available
in the schema but not separately rendered, since there is nothing
meaningful to show beyond the booking's own status at this stage.

## Version Checks

**None exist** — no `draft.version`/revision counter anywhere (unchanged
finding since CUSTOMER-L5-06). The real "lock" is not an optimistic
version check but the unconditional DB-unique constraints
(idempotency-contract.md) plus the draft's own terminal-status guard
(`_assert_not_terminal`, applied inside `mark_ready_for_confirmation`).

## Draft Final Status

`"confirmed"` — a real `TERMINAL_STATUSES` member (unchanged constant set
since CUSTOMER-L5-06). Set only **after** both `ServiceBooking` and
`ServiceJob` rows are flushed (`creation_service.py:143-167`) — this
client trusts this real, source-verified ordering rather than asserting
it independently (no live database transaction trace was performed this
sprint — see runtime-evidence.md).

## Rollback Behavior

Not directly observed (no live database). By construction (a single
`AsyncSession` used across the whole `finalize()` call, with the caller —
`confirm_draft`'s router function — issuing the final `await db.commit()`
only after `finalize()` returns successfully), a raised exception
anywhere inside `finalize()` before that final commit should roll back
every flushed-but-uncommitted change (both inserts, the draft mutation,
and the confirmation-lock insert) atomically, per standard SQLAlchemy
async-session semantics. This is a source-code-level inference, not a
live-tested guarantee — documented honestly as such in
runtime-evidence.md/known-gaps.md.
