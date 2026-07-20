# UX-05 Workstream Reconciliation (Round 6)

Mirrors UX-04A's reconciliation pattern: every numbered workstream from the original UX-05 brief gets one
explicit disposition, based on what's actually built and verified across six rounds (not aspirational). This is
what makes `STAFF_TECHNICIAN_APP_DESIGN_COMPLETE` claimable for the achievable subset, honestly separated from
what's genuinely blocked outside this phase's control.

**Dispositions used**: `IMPLEMENTED` (built, wired into real navigation, tested), `MOCK_DESIGN_ONLY` (built,
honestly fixture-backed, no live endpoint exists), `API_CONTRACT_REQUIRED` (blocked on a real, missing backend
endpoint — not closeable from the frontend), `PRODUCT_DECISION_REQUIRED` (needs a decision outside this phase's
authority), `NOT_APPLICABLE` (out of scope per a product correction), `PARTIAL` (real progress, real remaining
work, not a backend blocker), `DEFERRED` (not started, no blocker, just not reached).

| # | Workstream | Disposition | Evidence |
|---|---|---|---|
| 1 | Existing app audit (CSV) | IMPLEMENTED | `existing-screen-route-audit.csv` |
| 2 | IA + role-aware navigation | IMPLEMENTED | `RoleAwareTabNavigator`/`TechnicianTabNavigator`/`StaffTabNavigator`, mounted in `AppNavigator`, fail-closed |
| 3 | Auth/session states | PARTIAL | Login/loading/logout real (pre-existing `AuthContext`); session-expired/tenant-suspended/reauth-required are showcase-only (`SystemStatesShowcaseScreen`), not wired to real triggers |
| 4 | Configurable role-aware Home | PARTIAL | `HomeScreen` recomposed on real `groupJobs()` (technician); `StaffHomeScreen` is `API_CONTRACT_REQUIRED` (see #38) |
| 5 | Technician My Work | IMPLEMENTED | `JobsListScreen` wired to real `groupJobs()`, Current/Today/Upcoming/Needs Action/Completed tabs, real data |
| 6 | Staff Work Queue | API_CONTRACT_REQUIRED | `StaffWorkQueueScreen` exists, correctly shows restricted/empty — no live work-queue endpoint exists in `lib/api.ts` |
| 7 | Schedule | PARTIAL | `ScheduleScreen` real (Today/Upcoming, live `jobsApi` data); Day/Agenda views and conflict-detection logic not built |
| 8 | Pipeline-aware Job Detail | IMPLEMENTED (real-evidence-corrected) | `JobDetailScreen` extended with `PipelineBadge`/`CustomerContactCard`/`AddressCard`; single-pipeline correction documented in `pipeline-aware-job-detail.md` — no field_ops.Job surface built because none has live data |
| 9 | Current Job mode | IMPLEMENTED | `CurrentJobScreen`, sticky `NextActionBar`, real transitions |
| 10 | Status transition flows | IMPLEMENTED | Pre-existing `JobDetailScreen` transition grid + `CurrentJobScreen`'s `NextActionBar`, both real, using `lib/transitions.ts`'s real state machine |
| 11 | Customer/address access | IMPLEMENTED | `CustomerContactCard`/`AddressCard`, wired into `JobDetailScreen` + `CurrentJobScreen`; Call action correctly disabled (no phone data exists) |
| 12 | Inspection workflow | MOCK_DESIGN_ONLY | `InspectionForm` + `InspectionChecklistShowcaseScreen`, real draft persistence (AsyncStorage), no live inspection-content endpoint |
| 13 | Checklist execution | MOCK_DESIGN_ONLY | `ChecklistSection`/`ChecklistProgress`, real progress/validation logic (`checklist.ts`, tested), real draft persistence, no live endpoint |
| 14 | Parts Request creation | MOCK_DESIGN_ONLY | `PartsRequestShowcaseScreen`, no live parts-request endpoint anywhere in `lib/api.ts` |
| 15 | Parts Request tracking | MOCK_DESIGN_ONLY | `PartsRequestStatusCard`, technician-only `add_note` action type-enforced; same endpoint gap as #14 |
| 16 | Staff Parts Approval | API_CONTRACT_REQUIRED + PRODUCT_DECISION_REQUIRED | `StaffPartsApprovalShowcaseScreen` correctly fail-closed-restricted for every real account (no live role/permission field on `StaffUser` — see #38) |
| 17 | Quote presentation | MOCK_DESIGN_ONLY | `QuoteShowcaseScreen`, confirmed via full `lib/api.ts` re-read that no quote endpoint exists anywhere |
| 18 | Job notes | MOCK_DESIGN_ONLY | `JobNoteComposer`, internal/technician/customer_visible distinction enforced in both composition and display, no live endpoint |
| 19 | Job media | MOCK_DESIGN_ONLY | `MediaCaptureGrid`, never renders storage keys/signed URLs, never marks uploaded before backend confirmation (guards against a lying affordance even in mock form), no live endpoint |
| 20 | Notifications/action inbox | IMPLEMENTED | Real pre-existing `notificationsApi`; `NotificationsScreen` now uses the real `NotificationCard` + reactive theme (Round 6) |
| 21 | Availability/work-status | MOCK_DESIGN_ONLY | `AvailabilityControl`, confirmed no live work-status endpoint distinct from account/job status; wired into real `ProfileScreen` |
| 22 | Profile | PARTIAL | Extended with real `specialisations`, role/designation, `AvailabilityControl`, `ThemeToggle`; areas/certifications/recent-activity honestly `MOCK_DESIGN_ONLY` (no endpoint) |
| 23 | Offline/weak-network states | IMPLEMENTED (detection) + MOCK_DESIGN_ONLY (matrix enforcement) | Real `useNetworkStatus` (NetInfo, native+web), `NetworkStatusBanner` wired into production shell; `offline-operation-matrix.csv` documents the intended per-operation rule but no operation actually auto-replays/queues yet (correctly, per the hard constraint) |
| 24 | Readiness metadata | IMPLEMENTED | `ActionReadinessView`/`readiness` field present on every view model in `types/ux05.ts`; `readiness-state-registry.csv` |
| 25 | Typed view models | IMPLEMENTED | `src/types/ux05.ts`, all 20 named view models, real-evidence single-pipeline correction |
| 26 | Frontend adapter contracts | PARTIAL | Real API calls documented inline in `lib/api.ts` comments (pre-existing convention this app already followed); a separate formal adapter-contract doc per the brief's exact format was not written — the same information exists distributed across `backend-contract-blockers.md` + `readiness-state-registry.csv` instead |
| 27 | Shared mobile components | PARTIAL | 17 components built (`shared-mobile-component-inventory.csv`); ~5 more named in the brief (MobileAppShell, MobileStatusTimeline, ChecklistProgress separate from ChecklistSection, SyncConflictPanel, OfflineDraftBanner) not built as distinct components |
| 28 | System states | PARTIAL | `SystemStatesShowcaseScreen` covers Session Expired/Tenant Suspended/Read-only/Restricted as presentation; not wired to real triggers (no real session-expiry event, no real tenant-status field) |
| 29 | Light/dark themes | PARTIAL | Real mechanism built (Round 5): `ThemeContext`, dark palette, `ThemeToggle`. Reactive in: `AppNavigator`, both tab navigators, `PipelineBadge`, `PermissionRestrictedState`, `NetworkStatusBanner`, `NotificationCard`, `AvailabilityControl`, `NotificationsScreen` (Round 6). Still static-light-only: `HomeScreen`, `JobsListScreen`, `JobDetailScreen`, `ScheduleScreen`, `CurrentJobScreen`, most showcase screens, most of `ProfileScreen`'s own layout — real, disclosed, mechanical remaining work |
| 30 | Accessibility | PARTIAL | Real fixes: 4 touch-target corrections, `accessibilityRole`/`accessibilityLabel` on 9+ components, color-independent status. Not done: focus-order audit, text-scaling stress test, live screen-reader session (all require a device/emulator not available here) |
| 31 | Localization readiness | NOT_APPLICABLE | Round 6 product correction: Super Admin/Tenant/Staff/Technician apps are single-language by design; multilingual is DeepSeek-customer-chat-only. See `localization-readiness-report.md`. The Round 5 spot-check code/tests were kept (harmless) but this is a closed line item, not open scope |
| 32 | Development showcase screens (~30) | PARTIAL | 10 built (`development-showcase-inventory.csv`): Parts Request, Inspection & Checklist, Notes & Media, Staff Parts Approval, Current Job, Quote, Offline States, System States, Theme, Localization |
| 33 | Unit/component tests | IMPLEMENTED (for what's built) | 43 tests, real behavioral assertions (role fail-closed, explicit-deny, pipeline non-collapse, My Work classification, checklist validation, RNTL renders, draft-persistence restart simulation, localization non-truncation) |
| 34 | Runtime testing | IMPLEMENTED (Login-screen scope) | Real Playwright verification against the Expo web bundle, unblocked in Round 4, re-verified every round since including after Round 6's changes — zero errors. Scope limited to the unauthenticated Login screen (no `linking` config exists to deep-link into authenticated routes in-browser — see #26/`runtime-test-report.md`) |
| 35 | Offline testing | PARTIAL | Real network-state detection + real draft persistence with a genuine restart-simulation test; the fuller deterministic-scenario matrix from the brief (network-drop-during-draft, interrupted-media-upload, etc.) not individually built/tested |
| 36 | Build/regression verification | IMPLEMENTED | Install/typecheck/tests/build/runtime all proven real in WSL every round; `git diff --stat` non-change check against `7488335` re-confirmed empty every round; lint honestly `NOT_CONFIGURED` (real finding, not fabricated) |
| 37 | Non-change audit | IMPLEMENTED | `backend-non-change-report.md`, `frontend-file-allow-list.md`, re-verified fresh every round including after the Round 4→5 concurrent-process branch incident (never touched this branch) |
| 38 | Documentation (72 files) | PARTIAL | 43 files in `docs/design/ux-05-staff-technician-app/` by end of Round 6 (real `ls` count, not estimated) — of 72 originally listed |

## The two genuine backend-contract blockers (not closeable from the frontend)
1. **No StaffPermission-fetch endpoint** and **no role field on `StaffUser`** — blocks #6, #16, and any real
   staff-vs-technician distinction. `deriveRole()` fails closed to `technician` for every real account today;
   this is correct, safe behavior, not a bug, but it means `StaffHomeScreen`/`StaffWorkQueueScreen`/
   `StaffPartsApprovalShowcaseScreen` cannot show real content until the backend exposes this. **This is a
   backend team decision, outside this design phase's authority.**
2. **No content endpoint for inspection/checklist/quote/parts-request/notes/media** — every one of #12/13/14/
   15/17/18/19 is fully designed, componentized, and tested against fixture data, but has nothing real to call.
   **This is a backend team decision** (whether/how to build these endpoints), also outside this phase's
   authority.

Neither blocker is a reason to withhold `DESIGN_COMPLETE` for the frontend-achievable subset — forcing a fake
completion by inventing endpoints or fabricating data would violate the no-fabrication hard constraint. The
correct outcome, per the coordinator's framing, is exactly what this table shows: clean, honest
`API_CONTRACT_REQUIRED`/`PRODUCT_DECISION_REQUIRED` dispositions on the blocked items, `IMPLEMENTED` everywhere
that's genuinely true.

## What remains genuinely open (frontend-achievable, not backend-blocked)
- Dark-theme conversion of the remaining ~8 screens (mechanical, proven pattern — real work, not started for
  most of them).
- ~20 more showcase screens (breadth, not depth — the underlying components mostly already exist).
- ~24 more documentation files (some now trivial given #31's closure removes ~3 planned localization docs from
  the target entirely; the rest are real writing work).
- Auth/session state screens (#3) beyond the showcase-only presentation — would need real trigger wiring (token
  expiry detection, tenant-status field) which itself depends on backend fields that may or may not already
  exist (not fully investigated this round).
- A formal adapter-contract document (#26) in the brief's exact format (the information exists, just not in one
  consolidated file).
