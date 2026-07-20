# Approval Gate

Status: **STAFF_TECHNICIAN_APP_DESIGN_PARTIAL** (Round 7)

This phase does NOT certify the full UX-05 brief (~38 workstreams, ~72 docs, full runtime/offline/a11y test
matrix, 30 showcase screens) as complete. See `workstream-reconciliation.md` for the full 38-item disposition
table (mirroring UX-04A's pattern). Through seven rounds it certifies, with real evidence:

- A working WSL dependency-install pipeline, including Expo-web, Playwright, and NetInfo.
- A typed domain-model foundation reflecting real backend evidence (single live pipeline, real status literals).
- A fail-closed role/permission presentation layer, unit-tested.
- Role-aware navigation actually mounted and reachable.
- Home/My Work/Schedule/Current Job/Notifications all real, wired to live data, and now theme-reactive.
- Quote/Availability/Inspection/Checklist/Parts/Notes/Media all built, honestly `MOCK_DESIGN_ONLY`, verified
  against a full `lib/api.ts` re-read rather than assumed.
- **The full verification stack works end-to-end**, re-confirmed after every round including Round 7: install →
  typecheck → unit/component tests → Expo web bundle build → headless-browser runtime load, zero errors.
- **A genuine bug found and fixed via real browser verification** (Round 4).
- **A real, working dark-theme mechanism** (Round 5), now applied to 9 screens and 7 components (Round 7) —
  `AppNavigator`, both tab navigators, `HomeScreen`, `JobsListScreen`, `ScheduleScreen`, `CurrentJobScreen`,
  `ProfileScreen`, `NotificationsScreen`, plus `PipelineBadge`/`PermissionRestrictedState`/`NetworkStatusBanner`/
  `NotificationCard`/`AvailabilityControl`/`ScheduleCard`/`CustomerContactCard`/`AddressCard`.
- **Real `NetworkStatusBanner`** backed by `@react-native-community/netinfo` (native + web).
- **Real draft persistence** with a genuine restart-simulation test.
- **A real session-expired signal** (Round 7): `ServiceOSError` now carries the actual HTTP status;
  `AuthContext` sets `sessionExpired` only on a genuine 401; `LoginScreen` shows a real banner driven by it — not
  a mock trigger.
- **A formal `frontend-adapter-contract.md`** (Round 7) covering every real and MOCK_DESIGN_ONLY adapter.
- The language-architecture product correction applied: localization is `NOT_APPLICABLE` for this app, not an
  open workstream.
- 12 of ~30 dev showcase screens built. 46 of 72 doc files written.
- 43/43 tests passing, 19 typecheck errors (all pre-existing pattern, zero new), zero changes outside
  `mobile/staff-app/` and this doc directory — all re-verified fresh this round.

## Why this is not STAFF_TECHNICIAN_APP_DESIGN_COMPLETE
Per the coordinator's own framing: forcing a completion claim while material frontend-achievable work remains
would not be honest, even though the two genuine backend-contract blockers (StaffPermission/role endpoint;
content endpoints for inspection/checklist/quote/parts/notes/media) are correctly out of scope and don't block
completion by themselves. What genuinely remains, real and frontend-achievable, not backend-blocked:
- Dark-theme conversion of `JobDetailScreen` (deliberately deferred — it holds the real money-collection modal,
  and converting it without dedicated regression coverage was judged too risky this round), `LoginScreen`, most
  dev showcases, and 6 more ux05 components + the pre-existing shared component library
  (`Card`/`Button`/`StatCard`/`Skeleton`/`JobStatusBadge`).
- ~18 more showcase screens, ~27 more doc files.
- Real trigger wiring for tenant-suspended/account-disabled/reauthentication-required (blocked on whether the
  backend actually has the fields to drive them — not confirmed either way this round, a genuine open question
  rather than a backend refusal).

## Recommendation for a future UX-05B pass
This phase's foundation (typed view models, fail-closed role/permission layer, working WSL+Playwright
verification pipeline, real dark-theme mechanism, real component library, formal adapter contract) is solid and
proven across seven rounds. A follow-on pass should prioritize: (1) finishing `JobDetailScreen`'s theme
conversion with real regression testing given its financial-action surface, (2) the remaining showcase/doc
breadth, (3) investigating whether real tenant-status/account-status fields exist to wire the remaining
session-state triggers, (4) flagging the two backend-contract gaps to the backend team as concrete asks.
