# UX Program History (UX-01 through UX-07)

## UX-01 — Shared Design System / Foundation

- Goal: establish a shared design-token/theme system for web frontends.
- Note: this system is React-DOM/web-only; it is not directly usable inside
  the two Expo/React Native apps (Staff and Customer), which built their own
  local theme systems (UX-05, UX-07 Pass 2/3b respectively).

## UX-02 — Super Admin Foundation

- Goal: initial Super Admin frontend build-out.
- Later hardened in UX-07 Round 3/Pass 1: test infrastructure wired from zero
  to 13/13 passing, live access verified via real Playwright/Chromium.

## UX-03 — Tenant Portal Foundation

- Goal: initial Tenant Portal frontend build-out, later extended by UX-04.

## UX-04 — Tenant Operations (incl. UX-04A, UX-04B)

- Final commit: `7488335`
- Unit tests: 53/53
- Playwright: 87/87
- Build: passing
- Confirmed a real ancestor of the UX-08 baseline (`branch-worktree-baseline.md`).

## UX-05 — Staff/Technician Application (incl. 05B/05C finalization)

- Closure commit: `493a132` (`design/ux-05b-finalization`)
- Tests: 56/56
- Real login/session/logout, real Home and My Work, real ServiceJob workflow
  and status transitions, network and draft persistence.
- Known non-blocking backlog: **UX05-BL-001** (remaining Staff/Technician
  showcase-screen breadth, ~18/30 done) — logged, not executed, correctly
  not reopened by later phases.
- A real bug was found and fixed during manual review outside the agent
  loop: `authApi.login` called a nonexistent endpoint — repointed to the
  real `POST /v1/auth/login`.
- Confirmed a real ancestor of the UX-08 baseline.

## UX-06 — Customer Application

- Closure commit: `b426e08`
- **Final status: `CUSTOMER_APP_DESIGN_COMPLETE`** — this was a genuine,
  final closure at the time; UX-08 does not reopen or downgrade it.
- Tests at closure: 48/48; typecheck: 0 errors.
- Real authentication, real DeepSeek tool orchestration, real category/
  offering discovery, real serviceability, real server-authoritative
  pricing, real bargain and standard-price paths, real idempotent booking
  creation, real booking list/detail, refresh persistence.
- Real bookings created during closure verification: `BK-20260721-000005`,
  `BK-20260721-000006`.
- A real backend bug (`match_provider_and_price()` had no fallback when no
  `BargainRule` existed for an offering, e.g. `ac_repair`) was diagnosed
  during UX-06 and fixed on a separate backend branch
  (`fix/bargain-optional-price-path`) — not a UX-06 frontend defect.
- Confirmed a real ancestor of the UX-08 baseline. UX-07 later extended
  Customer dark mode, Home IA, navigation, accessibility and test coverage
  on top of this closure — those later improvements do not retroactively
  change UX-06's own closure evidence.

## UX-07 — Cross-App Production Readiness (Rounds 1-3, Round 4 Passes 1-3f)

- Final commit: `50fe95b` (this is UX-08's starting point)
- **Final status: `UX07_INTEGRATION_PARTIAL`** — preserved as-is, not
  rewritten as production-ready.
- Real, live, end-to-end operational loop proven: customer booking
  (`BK-20260721-000008`) → ServiceJob (`JOB-20260721-000008`) → full status-
  transition graph → `completed` → server-computed commission deduction
  (`-21.0` on a `775.0` job) → real customer review (`REV-56700400`,
  `pending`) via the canonical `POST /v1/customer/reviews`.
- Super Admin: 13/13 tests (root-caused 2 genuine test-infra bugs — a
  missing `ResizeObserver` mock and an ambiguous `getByText` match — no
  source component touched), live access verified via real Playwright.
- Customer-app dark mode: real `ThemeContext` (System/Light/Dark,
  AsyncStorage-persisted, no startup flash) rolled out across all screens;
  a genuine test flake (`Appearance.addChangeListener` left unmocked) was
  root-caused and fixed with 25/25 + 10/10 + 5/5 repeated-run proof.
- Customer Home rebuilt (real search, SmartBot CTA, real active-booking/
  empty states, no fabricated data) and SmartBot category-handoff wired
  (no re-asking a category the customer already picked on Home).
  Guided booking-flow (the real `chatBookingReducer`-driven modal, not the
  free-text DeepSeek chat, which has no backend-exposed question/options
  contract) got a header/progress/collapsed-summary restructure.
- Accessibility: 1 CRITICAL + 3 HIGH + 7 MEDIUM real findings fixed with
  actual `accessibilityLabel`/`accessibilityRole`/`accessibilityState`
  props on Home, SmartBot, and bottom navigation; some LOW items honestly
  left as known gaps.
- Customer tests grew from 48/48 (UX-06 closure) → 76/76 by UX-07's close,
  0 typecheck errors throughout, verified via repeated fresh installs at
  every pass.
- **Responsive certification was deliberately deferred** mid-program (user
  direction: certifying exact pixel widths is wasted effort since the
  Customer visual design will be replaced) — not a failure, a scope
  decision UX-08 formalizes and carries forward.
- Real web-rendered Playwright screenshot pair (light/dark login) captured
  via a genuine Expo web export — but the final authenticated Home/
  SmartBot visual sweep could not complete because the backend was
  unreachable from that verification environment at the time — disclosed
  honestly as an environment blocker, not skipped silently.
- Known backend-owned gaps carried forward (not fixed, since backend work
  was out of UX-07's scope): `offering_type_id` required-field contract
  inconsistency, `POST /v1/customer/reviews` raw 500 on malformed input,
  quote/checklist fixture-only behavior, technician parts-request creation
  gap, no customer cancellation/rescheduling capability.

## Summary table

| Phase | Final commit | Final status | Tests | Typecheck |
|---|---|---|---|---|
| UX-04 | `7488335` | Complete | 53/53 unit, 87/87 Playwright | passing build |
| UX-05 | `493a132` | Complete (UX05-BL-001 non-blocking backlog) | 56/56 | — |
| UX-06 | `b426e08` | `CUSTOMER_APP_DESIGN_COMPLETE` | 48/48 | 0 errors |
| UX-07 | `50fe95b` | `UX07_INTEGRATION_PARTIAL` | 76/76 | 0 errors |
