# Caller and Compatibility Regression

## Callers re-verified (unchanged from Slice 2F-14F's audit, re-confirmed after tightening)

1. **`POST /v1/jobs` (public route)** — booking-referenced and parent-derived modes bypass the
   relationship query entirely (the Booking/parent itself proves authority) — re-confirmed via
   `test_booking_referenced_creation_does_not_query_relationship`/
   `test_parent_derived_creation_does_not_query_relationship` (Slice 2F-14F, unmodified, still
   passing). Standalone mode now uses the tightened predicate — re-verified via this slice's own
   17 new tests, all passing.
2. **`FieldOpsService._spawn_repair_from_consultation`** (internal) — always supplies
   `parent_job_id`, never reaches the standalone relationship check at all — unaffected by this
   slice's tightening (confirmed, no fixture changes were needed for
   `tests/test_job_type_flows.py`'s consultation-spawn test).

## Confirmed

- No internal caller depends on a draft, rejected, cancelled, expired, voided, or generic-Job
  relationship row to succeed — all existing tests continue to pass using only
  `CONFIRMED`-status Bookings or `booking_id`/`parent_job_id`-set Jobs as evidence (the same
  fixtures Slice 2F-14F's own tests already used by default).
- No legitimate customer flow is accidentally blocked: Slice 2F-14F's own
  `test_customer_with_prior_tenant_booking_succeeds`/`test_customer_with_prior_tenant_job_succeeds`
  continue to pass unmodified (their mock Bookings/Jobs already used `BS.CONFIRMED`/qualifying
  lineage by construction, since 2F-14F's own fixture defaults already matched what this slice
  now requires — no fixture updates were needed for those two tests).
- No cross-pipeline adapter was introduced — the tightened queries reuse the existing `Booking`/
  `Job` models and the existing `BS` constants import.
