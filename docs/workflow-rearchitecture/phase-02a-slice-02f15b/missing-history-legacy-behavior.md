# Missing-History Legacy Row Behavior

| Legacy row shape | Field_ops relationship use | Direct field_ops.create_job(booking_id) | Booking.convert_to_job | Test |
|---|---|---|---|---|
| No `BookingStatusHistory` rows at all | Denied (JOIN drops the Booking; falls through to Job check; fails closed if none) | Denied (`creator_r.scalar_one_or_none()` returns `None`; `None != "customer"` is True; requires independent evidence) | Denied (same as above) | `test_no_history_row_at_all_fails_closed` |
| Creation row with `changed_by_role IS NULL` | Denied (`NULL == 'customer'` is false at SQL level) | Denied | Denied | `test_null_changed_by_role_fails_closed` |
| Creation row with `changed_by_role` unknown/invalid string (e.g. a stale role name) | Denied (equality filter only matches the literal string `"customer"`) | Denied | Denied | covered by the same equality-filter logic; no separate code path exists for "unknown" vs "wrong" role — both simply fail the `== "customer"` check |
| Only provider-confirmation history (no creation row recorded as customer) | Denied — requires independent evidence | Denied | Denied | `test_provider_confirmation_only_history_fails_closed` |
| Only customer-cancellation/reschedule history (no customer-authored creation row) | Denied — a cancellation/reschedule row never has `from_status IS NULL` (see `later-customer-activity-test-matrix.csv`), so it cannot satisfy the filter regardless of `changed_by_role` | Denied | Denied | `later-customer-activity-test-matrix.csv` |
| Conflicting creation-history rows (theoretical: two rows both with `from_status IS NULL` for one Booking, one customer- one provider-authored) | Would match the customer-authored one if it happens to exist — **not currently reachable via any writer path** (every writer call site in this codebase writes `_write_history` exactly once per Booking with `from_s=None`, only in `create_booking`); documented as a theoretical multiplicity risk, not fixed, since no code path can produce it | same | same | `booking-status-history-schema.md` (writer audit) — 6 total call sites, only 1 ever passes `from_s=None` |
| Seed/test-style history (arbitrary fixture data inserted directly, bypassing the service layer) | Whatever `changed_by_role` the seed data happens to record — the runtime code has no way to distinguish seed data from real application writes, and this is explicitly out of scope (no migration/audit of existing data was performed) | same | same | `product-decisions-required.md` |
| Unknown actor role / invalid actor ID | Denied (fails the `== "customer"` string equality regardless of what the invalid value is) | Denied | Denied | equality-filter reasoning above |

## Privacy-safe error
Every denial path raises the identical `ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED", ..., status_code=422)` — the error message never discloses which of the above conditions applied (missing history vs. wrong actor vs. provider-only history are all indistinguishable to the caller), matching the established privacy pattern from Slice 2F-14F/G.

## Conclusion
Every category of missing or ambiguous provenance **fails closed** — there is no code path where an unrecorded, incomplete, or non-customer-authored creation event allows relationship establishment, direct `create_job` use, or conversion.
