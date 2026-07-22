# Slice 2F-39A5 — Implementation Summary

## Sub-criterion achieved: `MOUNTED_ROUTE_CENSUS_COMPLETE`
## Overall program status: still `AUTHORIZATION_REMEDIATION_BLOCKED`

See `final-status-rationale.md` for why these two tokens are reported
together, not collapsed into one.

## What was achieved

1. **All 5 remaining `PRODUCT_DECISION_REQUIRED` routes resolved**,
   each backed by an explicit product/caller-policy decision — asked of
   the user directly, then delegated back to the assistant to apply the
   most defensible, fail-closed choice:
   - `platform_commerce.billing_endpoint::route_operation` →
     `require_super_admin` (matches sibling config routes).
   - `appointment.router::hold_slot` → tenant-ownership check added
     (corroborated by the already-frozen Slice 2F-26E manual-adjudication
     corpus, which independently expected exactly this fix).
   - `analytics.router::ingest_event` → `require_super_admin`.
   - `notification.router::send_notification`, `notification.router::retry`
     → both `require_super_admin`.
2. **7 new tests** prove all 4 fixes.
3. **3 classifier-corpus exemptions updated** for the `ingest_event` fix
   — this time affecting both `persona` and `tenant_direction` fields, a
   new variant of the forward-progress reclassification pattern seen in
   every prior slice of this arc.
4. **All 21 routes originally flagged by Slice 2F-39A3 now resolved**:
   14 fixed (9 in 2F-39A4, 5 here), 4 verified safe, 3 standing N01
   blocker (unchanged, out of scope).

## Evidence

- Phase-2F regression: **2526/2526 passed, twice, identical** — see
  `phase2f-regression-report.md`.
- Full backend regression: **byte-for-byte identical failure set** to
  Slice 2F-39A4's run (57 failed, 111 errors — all pre-existing baseline
  or `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED`, confirmed via direct
  diff and confirmed no failure names any of the 5 fixed routes) — see
  `full-backend-regression-diff.md`.
- 4 application files changed, 4 test files changed/added, 1 new script
  — see `backend-file-change-report.md`.
- Zero frontend/mobile/UX files touched — see
  `frontend-non-change-report.md`.

## Net effect on the certification ledger

`PRODUCT_DECISION_REQUIRED` count: 5 → **0**. Cumulative across the
2F-39A3 → 2F-39A5 arc: 21 originally-flagged routes, all resolved (14
fixed, 4 verified safe, 3 N01-standing). This slice stops at its own
approval gate; Slice 2F-39B (demo-role decisions + Migration 144 proof),
2F-39C (remaining complete-suite failures and the now-twice-reproduced
`LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED` instability), and Slice 2F-40
(final recertification) are not started.
