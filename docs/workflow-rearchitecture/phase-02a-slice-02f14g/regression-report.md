# Regression Report — Slice 2F-14G

## Slice-specific executions

- `tests/test_phase2f14g_field_ops_relationship_provenance.py` (17 tests, new) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` (34) — PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30, unmodified) — PASS.
- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` (21) — PASS.
- `tests/test_phase2f14c_field_ops_notes_media_and_create_job_fk.py` (12) — PASS.
- `tests/test_phase2f14d_field_ops_create_job_relational_consistency.py` (10) — PASS.
- `tests/test_phase2f14e_field_ops_source_eligibility_and_lineage.py` (31) — PASS.
- `tests/test_phase2f14f_field_ops_manual_customer_authority.py` (10, unmodified — no fixture
  changes were needed since 2F-14F's own default fixtures already used qualifying
  statuses/lineage) — PASS.
- `tests/test_job_type_flows.py`, `tests/test_job_type_routing.py`, `tests/test_usage_quota.py`
  (37, unaffected) — PASS.

Combined: **202 passed, 0 failed** (2F-14-series + job_type/usage_quota suites).

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request or booking"`:
**1698 passed, 7 skipped, 0 failed.**

## No fixture updates required

Unlike prior slices in this series, **no pre-existing test file required a fixture update** —
every existing test that reaches the relationship helper already used a `CONFIRMED`-status
Booking mock or a `booking_id`/`parent_job_id`-set Job mock by construction (Slice 2F-14F's own
defaults), which continue to qualify unchanged under this slice's tightened predicate.

## Net result

202 passed across direct slice/dependency suites (0 failures attributable to this slice); 1698
passed in the broad sweep, 0 failed.
