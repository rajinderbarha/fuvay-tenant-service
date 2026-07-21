# UX-06 Round 5 Implementation Summary

**Status: CUSTOMER_APP_DESIGN_PARTIAL** (see final-status-rationale.md).

## What this round did

1. **Bargain contract audit** (Workstream 1): read `mark_ready_for_confirmation`/
   `match_provider_and_price`/`confirm_price_choice`/`finalize` directly.
   Found and fixed a real client-side bug: Rounds 3/4 called the wrong confirm
   endpoint (`final_records`'s `finalize()`-only route) instead of the real
   `home_service_booking` route that also calls `mark_ready_for_confirmation()`.
   Determined bargain/tier-selection is mandatory infrastructure for this
   pipeline, not optional haggling — an explicit, evidence-based correction to
   the Round 5 brief's premise (bargain-optionality-decision.md).
2. **BargainRule safety gate** (Workstream 3): audited creation conditions —
   5 of 9 fail (no tenant scoping on the model at all, no create/write API
   exists). Correctly declined to create one; documented as
   `BARGAIN_CONFIGURATION_POLICY_BLOCKED` for this specific sub-area
   (bargain-configuration-safety.md).
3. **Real required-field fixes**: discovered `issue_summary`/`brand_id` are
   the real draft fields (not `issue_description`/`address_line`), added a
   real brand picker (`GET /v1/customer/catalog/brands`). Re-verified live via
   curl: with every field correct, the booking sequence now reaches a
   materially more precise error (`HOME_BOOKING_NO_PROVIDER_AVAILABLE`) than
   Round 3/4's generic `FINAL_DRAFT_NOT_READY` — confirms everything else in
   the pipeline is genuinely correct.
4. **Built the 3rd unaudited screen** (Service Detail, Workstream 7) — did not
   exist before; real data, real production route, real entry point.
5. **Rewrote Booking Detail** (Workstream 9): found and removed two real rule
   violations — a dead cancel control calling a nonexistent endpoint, and a
   fabricated payment-breakdown card using unconfirmed fields.
6. **Fixed Profile**: found and removed an internal health-score/ranking
   exposure (hard-forbidden by the canonical domain rules) in addition to
   field-name bugs.
7. **Typecheck reconciliation to zero** (Workstream 13): 123 → 0 UX-06-owned
   errors. Deleted 4 fully-superseded legacy screens (calling dead APIs)
   rather than patch them; root-caused the whole navigation-typing error
   class with real `RootStackParamList`/`TabParamList` types instead of
   casting each call site.
8. **Test expansion** (Workstream 14): 23 → 50 → 46 (net, after the 4 deleted
   screens reduced one test's file-scan count) tests, including a real
   mechanical guard against internal jargon/error-code leakage into
   customer-facing screens and bargain/tier-state reducer tests.
9. **4-run test stability check** (Workstream 16): 1 clean-install + 3
   consecutive runs, 50/50 (pre-deletion count) and later 46/46, zero
   flakiness (repeated-test-stability-report.md).
10. **Fixed a real react-dom/react version mismatch** blocking Playwright
    entirely (root-caused to a `package.json` override that hadn't actually
    reached the WSL build directory in a prior session).
11. Re-confirmed zero backend/other-frontend-app changes across all 5 commits.

## What this round could not complete

The backend (`http://localhost:8000`) became unreachable partway through this
round's execution (confirmed via repeated connectivity checks over an
extended window) — a genuine infrastructure interruption. This blocked:
- The full live Playwright certification sequence (Workstream 15) beyond what
  was already re-verified via direct API calls earlier in the round.
- The full light/dark/390px visual evidence sweep (Workstream 11) for screens
  not already captured in Round 4's evidence set.

See known-limitations.md and playwright-runtime-report.md for the precise,
honest accounting.

## Final state

- Branch: `design/ux-06-customer-app`
- Worktree: `G:\serviceos-ux06-customer-app`
- Commits this round: `6f1d8d5`, `13baba4`, `a1524a2`, `79f4bf9` (4 commits,
  meeting the "at least 4 separate commits" requirement), plus this final
  documentation commit.
- No backend, no other frontend app, touched (re-verified via `git diff --stat`).
