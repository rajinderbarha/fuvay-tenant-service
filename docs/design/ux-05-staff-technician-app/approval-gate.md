# Approval Gate

Status: **STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** (Round 3)

This phase does NOT certify the full UX-05 brief (~38 workstreams, ~72 docs, full runtime/offline/a11y test
matrix, 30 showcase screens) as complete. Through three rounds it certifies, with real evidence:

- A working WSL dependency-install pipeline for `mobile/staff-app`, including Expo-web dependencies and Playwright.
- A typed domain-model foundation reflecting real backend evidence (single live pipeline, real status literals).
- A fail-closed role/permission presentation layer, unit-tested.
- Role-aware navigation actually mounted and reachable.
- **Both flagged "logic built but not wired" gaps from Round 2 are now closed**: `HomeScreen` and
  `JobsListScreen` both render from the same real, tested `groupJobs()` classification.
- **Current Job mode** — a real focused single-job screen with a sticky primary action, built and wired into
  navigation.
- **Quote presentation and Availability control** — both built as honestly-labeled `MOCK_DESIGN_ONLY` (confirmed,
  by re-reading `lib/api.ts` in full, that neither has any live backend support), consuming real components with
  real behavioral tests, not fabricated as production-ready.
- **Profile screen extended** with real data (`specialisations`) where it exists, honestly labeled placeholders
  where it doesn't.
- **The Expo web build pipeline is proven to work end-to-end** — a real 3.1MB bundle, verified to contain this
  round's actual compiled source, served over HTTP. The remaining Playwright runtime check hit one specific,
  diagnosed, reproducible environment blocker (missing sudo access to install Chromium's system dependencies) —
  documented precisely rather than left ambiguous.
- 35/35 tests passing, re-verified fresh this round; 19 typecheck errors, all pre-existing pattern, zero new
  business-logic errors, re-verified fresh this round.
- Zero changes outside `mobile/staff-app/` and this doc directory, re-verified this round.

See `deferred-items.md` for what remains before a full `DESIGN_COMPLETE` gate: `StaffHomeScreen`/
`StaffWorkQueueScreen` still need a real backend endpoint (not a frontend gap), most of the a11y/theme/
localization workstreams, ~23 more showcase screens, and ~35 more doc files. Recommend continuing this exact
phase (same branch, same conventions) in a follow-on run, and separately flagging the staff work-queue-summary
and StaffPermission-fetch endpoints as real backend-contract needs for this design to fully close.
