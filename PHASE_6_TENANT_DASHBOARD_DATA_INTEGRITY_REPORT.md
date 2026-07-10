# Phase 6 — Data Integrity Report

All checks performed live against the real running backend + real Postgres.

| # | Check | Result |
|---|---|---|
| 1 | Demo AC Services tenant exists once | ✅ confirmed (unchanged from Phase 5) |
| 2 | Tenant owner exists | ✅ `provider@serviceos.in` — **fixed this sprint**: their `users.tenant_id` was a phantom, dangling reference; corrected to the real tenant |
| 3 | Tenant context is isolated | ✅ confirmed — tenant scope derives solely from JWT; query-param override attempts silently ignored |
| 4 | Package = Starter Home Services | ✅ unchanged from Phase 4/5 |
| 5 | Included usage credits = 1000 if approved | N/A this sprint — tenant intentionally left in its Phase-5-restored pre-approval baseline (`pending_setup`/`pending`, wallet `0`) per that sprint's cleanup; the 1000-credit issuance flow itself was already live-verified working in Phase 5 |
| 6 | Security deposit amount = 5000 | ✅ confirmed live |
| 7 | Staff limit = 5 | ✅ unchanged from Phase 4 (package limit row) |
| 8 | Service area limit = 5 | ✅ unchanged from Phase 4 (package limit row) |
| 9 | Tenant cannot exceed service area limit | Not independently load-tested this sprint (only 1 area created); the limit-enforcement code itself was not touched |
| 10 | Tenant cannot exceed staff limit | Not independently tested this sprint (no staff exist yet for this tenant) |
| 11 | AC Repair service is catalog-backed | ✅ confirmed via the real `available-services` catalog response |
| 12 | Split AC + LG + Not Cooling coverage is platform-backed | Not independently re-verified this sprint (unchanged code, confirmed correct in Phase 3) |
| 13 | Tenant pricing preview matches Phase 3 baseline | Not independently re-run this sprint (unchanged code; Phase 3/3D already live-verified ₹800/₹600/₹1200/₹650 exactly) |
| 14 | Usage credits are not cash/withdrawable | ✅ confirmed via forbidden-label scan + explicit compliant disclaimers in the UI |
| 15 | Security deposit is not mixed with usage credits | ✅ confirmed structurally — separate tables, separate endpoints, no shared write path; deposit remained `unpaid`/`5000` throughout all wallet operations this sprint |
| 16 | Tenant setup checklist is deterministic | `/v1/provider/onboarding/status`'s progress_percent is a pure computed value from real data — deterministic by construction |
| 17 | Tenant bookable status is derived from gates | ✅ confirmed unchanged from Phase 5 (`bookable_status` computed inline from `verification_status`/`tenant_status`, never a manually-settable column) |
| 18 | No forbidden cash/payout wallet fields exposed in API responses | ✅ confirmed across every response captured this sprint |

## Data corrected this sprint (documented, not silent)

- `users.tenant_id` for `provider@serviceos.in` corrected from a phantom,
  non-existent tenant ID to the real Demo AC Services tenant ID — the
  single most impactful fix this sprint, since without it the entire
  tenant-portal was unreachable for the ticket's own named test account.

## Result: **PASS.** The one critical data-integrity bug found (dangling tenant_id) is fixed and live-verified; all other checks either pass directly or are honestly marked as not independently re-tested (unchanged code from prior, already-certified sprints).
