# Deferred Items — Slice 2F-39A5

- N01 media routes remain deferred to N01's own remediation track,
  unchanged (3 rows, standing `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`).
- A dedicated `verify_2f39a5.py`.
- Slice 2F-39B: demo-account role decisions and Migration 144 PostgreSQL
  proof.
- Slice 2F-39C: remaining complete-suite failures and
  `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED` (reproduced identically
  across two independent full-suite runs now — 2F-39A4 and 2F-39A5 —
  useful evidence that the root cause is deterministic, not random flake).
- Slice 2F-40: final application-wide authorization recertification —
  not started, per the reviewer's sequencing should not start before
  2F-39B and 2F-39C.
- All items already deferred by 2F-39/2F-39A/2F-39A2/2F-39A2R/2F-39A3/2F-39A4
  remain deferred, unchanged, except the 5 routes resolved in this slice.
