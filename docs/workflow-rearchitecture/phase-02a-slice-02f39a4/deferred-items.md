# Deferred Items — Slice 2F-39A4

- Resolve the 5 remaining `PRODUCT_DECISION_REQUIRED` routes, prioritizing
  `platform_commerce.billing_endpoint::route_operation` (HIGH risk).
- N01 media routes remain deferred to N01's own remediation track,
  unchanged.
- A dedicated `verify_2f39a4.py`.
- Slice 2F-39B: demo-account role decisions and Migration 144 PostgreSQL
  proof.
- Slice 2F-39C: remaining complete-suite failures and test-order pollution
  (the `test_p0_notification_template_center.py` anomaly flagged
  `PRE_EXISTING_TEST_ORDER_POLLUTION` in Slice 2F-39A3 remains open),
  **plus a newly observed live-server-capacity instability**: this
  slice's full backend run showed 31 additional failures + 111 errors
  beyond the 26-failure baseline, all `httpcore.ConnectTimeout` inside
  `TestLive`-suffixed tests during a long (~15.5 min) run — see
  `full-backend-regression-diff.md`. Confirmed unrelated to this slice's
  9 fixes; needs investigation of live-test-server capacity/timeout
  configuration under long full-suite runs.
- Slice 2F-40: final application-wide authorization recertification —
  not started, and per the reviewer's sequencing should not start before
  2F-39B and 2F-39C.
- All items already deferred by 2F-39/2F-39A/2F-39A2/2F-39A2R/2F-39A3
  remain deferred, unchanged, except the 9 routes resolved in this slice.
